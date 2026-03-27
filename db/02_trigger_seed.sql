CREATE OR REPLACE FUNCTION get_transaction_type(id INTEGER)
RETURNS transaction_type.code%type
LANGUAGE SQL 
BEGIN ATOMIC
 SELECT CODE FROM TRANSACTION_TYPE WHERE id = get_transaction_type.id;
END;

CREATE OR REPLACE FUNCTION get_tax_bracket(portfolio_id INTEGER)
RETURNS tax_rate.rate%type
LANGUAGE SQL
BEGIN ATOMIC
 SELECT RATE 
    FROM TAX_RATE 
    WHERE ID = (SELECT tax_rate_id 
                FROM PORTFOLIO 
                WHERE id = get_tax_bracket.portfolio_id);
END;

--TRIGGER FUNCTIONS
CREATE OR REPLACE FUNCTION fnc_calc_transaction_data() 
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_tax_rate tax_rate.rate%type;
    v_transaction_type_code transaction_type.code%type;
    v_position_quantity transaction.quantity%type;
    v_quantity_cnt INTEGER;
    v_tax_base_comp FINANCIAL := 0;
    lot RECORD;
BEGIN
    v_tax_rate := get_tax_bracket(NEW.portfolio_id);
    v_transaction_type_code := get_transaction_type(NEW.transaction_type_id);

    NEW.total_amount := (NEW.price * NEW.quantity) + NEW.fee;

    -- tax_amount in case of selling calculated and updated based on tax lots
    IF v_transaction_type_code IN ('DIV', 'INT') AND v_tax_rate <> 0 THEN
        NEW.tax_amount := ROUND((NEW.price * NEW.quantity) * (v_tax_rate / 100), 2);
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

        IF v_tax_rate <> 0 THEN
            v_quantity_cnt := NEW.quantity;
            v_tax_base_comp := 0;

            FOR lot IN SELECT id, quantity, price, tax_base_amount 
                        FROM TAX_LOT 
                        WHERE asset_id = NEW.asset_id 
                        AND portfolio_id = NEW.portfolio_id
                        AND currency = NEW.currency
                        ORDER BY DATE ASC  -- FIFO approach
            LOOP
                IF v_quantity_cnt >= lot.quantity THEN
                    v_tax_base_comp := v_tax_base_comp + lot.tax_base_amount;
                    v_quantity_cnt := v_quantity_cnt - lot.quantity;
                ELSE
                    -- final, partial tax lot 
                    v_tax_base_comp := v_tax_base_comp + ROUND(v_quantity_cnt * lot.price, 2);
                    EXIT;
                END IF;
            END LOOP;

        NEW.tax_amount := ROUND(((NEW.price * NEW.quantity)-v_tax_base_comp) * (v_tax_rate / 100));
        END IF;
    END IF;

	RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_create_booking()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_transaction_type_code transaction_type.code%type;
    v_asset_type_code asset_type.code%type;
BEGIN
    v_transaction_type_code = get_transaction_type(NEW.transaction_type_id);

    SELECT code INTO v_asset_type_code
    FROM ASSET_TYPE
    WHERE ID = (SELECT asset_type_id FROM ASSET
                WHERE id = NEW.asset_id);

    -- @TODO: add booking matrix table to replace giant case here
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_calc_tax_lot()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $$
DECLARE
    v_tax_rate tax_rate.rate%type;
    v_transaction_type_code transaction_type.code%type;
    v_quantity_cnt INTEGER;
    --v_tax_base_comp FINANCIAL := 0;
    lot RECORD;
BEGIN
    -- tax on DIV and INT calculated directly in transaction trigger
    v_tax_rate = get_tax_bracket(NEW.portfolio_id);
    v_transaction_type_code = get_transaction_type(NEW.transaction_type_id);

    IF v_transaction_type_code = 'BUY' AND v_tax_rate <> 0 THEN
        INSERT INTO TAX_LOT(
         asset_id, 
         portfolio_id, 
         transaction_id,
         date, 
         currency, 
         quantity, 
         price, 
         tax_base_amount)
        VALUES (
         NEW.asset_id, 
         NEW.portfolio_id,
         NEW.id,
         NEW.date, 
         NEW.currency, 
         NEW.quantity, 
         NEW.price, 
         NEW.quantity * NEW.price);

    ELSIF v_transaction_type_code = 'SEL' AND v_tax_rate <> 0 THEN
        v_quantity_cnt = NEW.quantity;

        FOR lot IN SELECT id, quantity, price, tax_base_amount 
                   FROM TAX_LOT 
                   WHERE asset_id = NEW.asset_id 
                   AND portfolio_id = NEW.portfolio_id
                   AND currency = NEW.currency
                   ORDER BY DATE ASC  -- FIFO approach
        LOOP
            IF v_quantity_cnt >= lot.quantity THEN
                --v_tax_base_comp := v_tax_base_comp + lot.tax_base_amount;
                v_quantity_cnt := v_quantity_cnt - lot.quantity;
                DELETE FROM TAX_LOT WHERE id = lot.id;
            ELSE
                -- final, partial tax lot 
                --v_tax_base_comp := v_tax_base_comp + ROUND(v_quantity_cnt * lot.price, 2);
                UPDATE TAX_LOT SET 
                quantity = lot.quantity - v_quantity_cnt,
                tax_base_amount = ROUND((lot.quantity - v_quantity_cnt) * lot.price ,2)
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
    SELECT id INTO v_asset_type
    FROM ASSET_TYPE 
    WHERE code = NEW.asset_type_code;

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

-- TRIGGERS
CREATE OR REPLACE TRIGGER trg_calc_transaction
BEFORE INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_transaction_data();

CREATE OR REPLACE TRIGGER trg_booking
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_create_booking();

CREATE OR REPLACE TRIGGER trg_calc_tax_lot
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_tax_lot();

CREATE OR REPLACE TRIGGER trg_stg_asset_data
AFTER INSERT ON STG_ASSET_DATA
FOR EACH ROW
EXECUTE FUNCTION fnc_process_stg_asset_data()