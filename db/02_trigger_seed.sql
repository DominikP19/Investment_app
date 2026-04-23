CREATE OR REPLACE FUNCTION get_transaction_type(id INTEGER)
RETURNS transaction_type.code%type
LANGUAGE SQL 
BEGIN ATOMIC
    SELECT code 
    FROM TRANSACTION_TYPE 
    WHERE id = get_transaction_type.id;
END;

CREATE OR REPLACE FUNCTION get_transaction_type_id(transaction_code TEXT)
RETURNS transaction_type.id%type
LANGUAGE SQL AS $$
    SELECT id 
    FROM TRANSACTION_TYPE 
    WHERE code = $1;
$$;

CREATE OR REPLACE FUNCTION get_tax_bracket(portfolio_id INTEGER)
RETURNS tax_rate.rate%type
LANGUAGE SQL
BEGIN ATOMIC
 SELECT rate 
    FROM TAX_RATE 
    WHERE ID = (SELECT tax_rate_id 
                FROM PORTFOLIO 
                WHERE id = get_tax_bracket.portfolio_id);
END;

CREATE OR REPLACE FUNCTION get_portfolio_id(portoflio_name TEXT)
RETURNS portfolio.id%type
LANGUAGE SQL AS $$
    SELECT id 
    FROM PORTFOLIO 
    WHERE name = $1;
$$;

CREATE OR REPLACE FUNCTION get_asset_type_id(asset_type_code TEXT)
RETURNS asset.id%type
LANGUAGE SQL AS $$
    SELECT id
    FROM ASSET_TYPE
    WHERE code = $1;
$$;

CREATE OR REPLACE FUNCTION get_asset_type_code_from_asset_id(asset_id INTEGER)
RETURNS asset_type.code%type
LANGUAGE SQL AS $$
    SELECT code
    FROM ASSET_TYPE
    WHERE id = (
        SELECT asset_type_id
        FROM ASSET
        WHERE id = $1
    );
$$;

CREATE OR REPLACE FUNCTION get_asset_id(asset_name TEXT, currency TEXT)
RETURNS asset.id%type
LANGUAGE SQL AS $$
    SELECT id
    FROM ASSET
    WHERE name = $1
    AND currency = $2;
$$;

-- TRIGGER FUNCTIONS
CREATE OR REPLACE FUNCTION fnc_calc_transaction_data() 
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_tax_rate tax_rate.rate%type;
    v_transaction_type_code transaction_type.code%type;
    v_position_quantity transaction.quantity%type;
    v_quantity_cnt INTEGER;
    v_cost_base_comp FINANCIAL := 0;
    lot RECORD;
BEGIN
    v_tax_rate := get_tax_bracket(NEW.portfolio_id);
    v_transaction_type_code := get_transaction_type(NEW.transaction_type_id);

    NEW.total_amount := (NEW.price * NEW.quantity) + NEW.fee;

    -- tax_amount in case of selling calculated and updated based on tax lots
    IF v_transaction_type_code IN ('DIV', 'INT') AND v_tax_rate <> 0 THEN
        NEW.tax_amount := ROUND((NEW.price) * (v_tax_rate / 100), 2);
    END IF;

    IF v_transaction_type_code = 'SEL' THEN
        SELECT 
        sum(CASE WHEN tt.code = 'SEL' THEN (-1) * t.quantity ELSE t.quantity END) INTO v_position_quantity
        FROM TRANSACTION t
        INNER JOIN TRANSACTION_TYPE tt
        ON t.transaction_type_id = tt.id
        WHERE 
            t.portfolio_id = NEW.portfolio_id
        AND t.asset_id = NEW.asset_id
        AND t.currency = NEW.currency
        AND tt.code IN ('BUY', 'SEL');

        IF NEW.quantity > COALESCE(v_position_quantity, 0) THEN
        -- @TODO: add logging
            RAISE EXCEPTION 'Trying to sell % when overall holding is %', NEW.quantity, v_position_quantity;
        END IF;

        
        v_quantity_cnt := NEW.quantity;
        v_cost_base_comp := 0;

        FOR lot IN SELECT id, quantity, price, cost_base_amount 
                    FROM TRANSACTION_LOT 
                    WHERE asset_id = NEW.asset_id 
                    AND portfolio_id = NEW.portfolio_id
                    AND currency = NEW.currency
                    ORDER BY DATE ASC  -- FIFO approach
        LOOP
            IF v_quantity_cnt >= lot.quantity THEN
                v_cost_base_comp := v_cost_base_comp + lot.cost_base_amount;
                v_quantity_cnt := v_quantity_cnt - lot.quantity;
            ELSE
                -- final, partial tax lot 
                v_cost_base_comp := v_cost_base_comp + ROUND(v_quantity_cnt * lot.price, 2);
                EXIT;
            END IF;
        END LOOP;

        NEW.transaction_result := ROUND((NEW.price * NEW.quantity) - v_cost_base_comp - COALESCE(NEW.fee, 0), 2);

        IF v_tax_rate <> 0 THEN
            NEW.tax_amount := ROUND(((NEW.price * NEW.quantity)-v_cost_base_comp) * (v_tax_rate / 100));
            IF NEW.tax_amount < 0 THEN
                NEW.tax_amount := 0;
            END IF;
        END IF;
    END IF;

	RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_calc_transaction_lot()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $$
DECLARE
    v_transaction_type_code transaction_type.code%type;
    v_quantity_cnt INTEGER;
    lot RECORD;
BEGIN
    -- tax on DIV and INT calculated directly in transaction trigger
    v_transaction_type_code = get_transaction_type(NEW.transaction_type_id);

    IF v_transaction_type_code = 'BUY' THEN
        INSERT INTO TRANSACTION_LOT(
         asset_id, 
         portfolio_id, 
         transaction_id,
         date, 
         currency, 
         quantity, 
         price, 
         cost_base_amount)
        VALUES (
         NEW.asset_id, 
         NEW.portfolio_id,
         NEW.id,
         NEW.date, 
         NEW.currency, 
         NEW.quantity, 
         NEW.price, 
         NEW.quantity * NEW.price);

    ELSIF v_transaction_type_code = 'SEL' THEN
        v_quantity_cnt = NEW.quantity;

        FOR lot IN SELECT id, quantity, price, cost_base_amount 
                   FROM TRANSACTION_LOT 
                   WHERE asset_id = NEW.asset_id 
                   AND portfolio_id = NEW.portfolio_id
                   AND currency = NEW.currency
                   ORDER BY DATE ASC  -- FIFO approach
        LOOP
            IF v_quantity_cnt >= lot.quantity THEN
                v_quantity_cnt := v_quantity_cnt - lot.quantity;
                DELETE FROM TRANSACTION_LOT WHERE id = lot.id;
            ELSE
                -- final, partial tax lot
                UPDATE TRANSACTION_LOT SET 
                quantity = lot.quantity - v_quantity_cnt,
                cost_base_amount = ROUND((lot.quantity - v_quantity_cnt) * lot.price ,2)
                WHERE id = lot.id;

            EXIT;
            END IF;

        END LOOP;

    END IF;

    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_process_stg_asset_data()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_asset_type asset_type.id%type;
    v_asset asset%rowtype;
    v_asset_id asset.id%type;
BEGIN
    v_asset_type = get_asset_type_id(NEW.asset_type_code);

    IF v_asset_type IS NULL THEN
        RAISE EXCEPTION 'Trying to isnert non-existent asset_type_code %', NEW.asset_type_code;
    END IF;

    SELECT * INTO v_asset
    FROM ASSET
    WHERE TRIM(both from lower(name)) = TRIM(both from lower(NEW.name))
    AND currency = NEW.currency
    AND asset_type_id = v_asset_type;

    IF v_asset.id IS NULL THEN
        INSERT INTO ASSET (name, isin, ticker, asset_type_id, currency)
        VALUES (
            NEW.name,
            NEW.isin,
            NEW.ticker,
            v_asset_type,
            NEW.currency
        ) RETURNING id INTO v_asset_id;
        IF NEW.price IS NOT NULL THEN
            INSERT INTO ASSET_VALUATION (asset_id, date, currency, price)
            VALUES (
                v_asset_id,
                NEW.date,
                NEW.currency,
                NEW.price
            );
        END IF;
    ELSIF v_asset.id IS NOT NULL THEN
        IF NEW.price IS NOT NULL THEN
            INSERT INTO ASSET_VALUATION (asset_id, date, currency, price)
            VALUES (
                v_asset.id,
                NEW.date,
                NEW.currency,
                NEW.price
            );
        END IF;
    END IF;

    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_validate_stg_transaction_data()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_transaction_type_id   transaction.id%type;
    v_portfolio_id          portfolio.id%type;
    v_asset_id              asset.id%type;
BEGIN
    v_transaction_type_id = get_transaction_type_id(NEW.transaction_type_code);
    v_portfolio_id = get_portfolio_id(NEW.portfolio_name);
    v_asset_id = get_asset_id(NEW.asset_name, NEW.currency);

    IF v_asset_id IS NULL THEN
        RAISE EXCEPTION 'Trying to insert non-exisisting asset %', NEW.asset_name;
    END IF;

    IF v_transaction_type_id IS NULL THEN
        RAISE EXCEPTION 'Trying to insert non-existing transaction_type_code %', NEW.transaction_type_code;
    END IF;

    IF v_portfolio_id IS NULL THEN
        RAISE EXCEPTION 'Trying to insert into non-existing portfolio %', NEW.portfolio_name;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_process_stg_transaction_data()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_transaction_type_id   transaction.id%type;
    v_portfolio_id          portfolio.id%type;
    v_asset_id              asset.id%type;
BEGIN
    v_transaction_type_id = get_transaction_type_id(NEW.transaction_type_code);
    v_portfolio_id = get_portfolio_id(NEW.portfolio_name);
    v_asset_id = get_asset_id(NEW.asset_name, NEW.currency);

    INSERT INTO TRANSACTION (
        date,
        description,
        transaction_type_id,
        asset_id,
        quantity,
        currency,
        price,
        fee,
        tax_amount,
        portfolio_id
    ) VALUES (
        NEW.date,
        'Imported from CSV',
        v_transaction_type_id,
        v_asset_id,
        NEW.quantity,
        NEW.currency,
        NEW.price,
        NEW.fee,
        NEW.tax_amount,
        v_portfolio_id
    );

    RETURN NULL;
END;
$$;

-- TRIGGERS
CREATE OR REPLACE TRIGGER trg_calc_transaction
BEFORE INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_transaction_data();

CREATE OR REPLACE TRIGGER trg_calc_transaction_lot
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_transaction_lot();

CREATE OR REPLACE TRIGGER trg_stg_asset_data
AFTER INSERT ON STG_ASSET_DATA
FOR EACH ROW
EXECUTE FUNCTION fnc_process_stg_asset_data();

CREATE OR REPLACE TRIGGER trg_validate_stg_transaction_data
BEFORE INSERT ON STG_TRANSACTION_DATA
FOR EACH ROW
EXECUTE FUNCTION fnc_validate_stg_transaction_data();

CREATE OR REPLACE TRIGGER trg_stg_transaction_data
AFTER INSERT OR UPDATE ON STG_TRANSACTION_DATA
FOR EACH ROW
EXECUTE FUNCTION fnc_process_stg_transaction_data();