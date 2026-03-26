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
    TAX_BRACKET tax_rate.rate%type;
    TRANSACTION_TYPE_CODE transaction_type.code%type;
    POSITION_QUANTITY transaction.quantity%type;
    QUANTITY_CNT INTEGER;
    TAX_BASE_COMP FINANCIAL := 0;
    lot RECORD;
BEGIN
    TAX_BRACKET := get_tax_bracket(NEW.portfolio_id);
    TRANSACTION_TYPE_CODE := get_transaction_type(NEW.transaction_type_id);

    NEW.total_amount := (NEW.price * NEW.quantity) + NEW.fee;

    -- tax_amount in case of selling calculated and updated based on tax lots
    IF TRANSACTION_TYPE_CODE IN ('DIV', 'INT') AND TAX_BRACKET <> 0 THEN
        NEW.tax_amount := ROUND((NEW.price * NEW.quantity) * (TAX_BRACKET / 100), 2);
    END IF;

    IF TRANSACTION_TYPE_CODE = 'SEL' THEN
        SELECT 
        sum(CASE WHEN tt.code = 'SEL' THEN (-1) * t.quantity ELSE t.quantity END) INTO POSITION_QUANTITY
        FROM TRANSACTION t
        INNER JOIN TRANSACTION_TYPE tt
        ON t.transaction_type_id = tt.id
        WHERE 
            t.portfolio_id = NEW.portfolio_id
        AND t.asset_id = NEW.asset_id
        AND t.currency = NEW.currency
        AND tt.code IN ('BUY', 'SEL');

        IF NEW.quantity > COALESCE(POSITION_QUANTITY, 0) THEN
        -- @TODO: add logging
            RAISE EXCEPTION 'Trying to sell % when overall holding is %', NEW.quantity, POSITION_QUANTITY;
        END IF;

        IF TAX_BRACKET <> 0 THEN
            QUANTITY_CNT := NEW.quantity;
            TAX_BASE_COMP := 0;

            FOR lot IN SELECT id, quantity, price, tax_base_amount 
                        FROM TAX_LOT 
                        WHERE asset_id = NEW.asset_id 
                        AND portfolio_id = NEW.portfolio_id
                        AND currency = NEW.currency
                        ORDER BY DATE ASC  -- FIFO approach
            LOOP
                IF QUANTITY_CNT >= lot.quantity THEN
                    TAX_BASE_COMP := TAX_BASE_COMP + lot.tax_base_amount;
                    QUANTITY_CNT := QUANTITY_CNT - lot.quantity;
                ELSE
                    -- final, partial tax lot 
                    TAX_BASE_COMP := TAX_BASE_COMP + ROUND(QUANTITY_CNT * lot.price, 2);
                    EXIT;
                END IF;
            END LOOP;

        NEW.tax_amount := ROUND(((NEW.price * NEW.quantity)-TAX_BASE_COMP) * (TAX_BRACKET / 100));
        END IF;
    END IF;

	RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_create_booking()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    TRANSACTION_TYPE_CODE transaction_type.code%type;
    ASSET_TYPE_CODE asset_type.code%type;
BEGIN
    TRANSACTION_TYPE_CODE = get_transaction_type(NEW.transaction_type_id);
    SELECT code INTO TRANSACTION_TYPE_CODE 
    FROM TRANSACTION_TYPE 
    WHERE ID = NEW.transaction_type_id;

    SELECT code INTO ASSET_TYPE_CODE
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
    TAX_BRACKET tax_rate.rate%type;
    TRANSACTION_TYPE_CODE transaction_type.code%type;
    QUANTITY_CNT INTEGER;
    TAX_BASE_COMP FINANCIAL := 0;
    lot RECORD;
BEGIN
    -- tax on DIV and INT calculated directly in transaction trigger
    TAX_BRACKET = get_tax_bracket(NEW.portfolio_id);
    TRANSACTION_TYPE_CODE = get_transaction_type(NEW.transaction_type_id);

    IF TRANSACTION_TYPE_CODE = 'BUY' AND TAX_BRACKET <> 0 THEN
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

    ELSIF TRANSACTION_TYPE_CODE = 'SEL' AND TAX_BRACKET <> 0 THEN
        QUANTITY_CNT = NEW.quantity;

        FOR lot IN SELECT id, quantity, price, tax_base_amount 
                   FROM TAX_LOT 
                   WHERE asset_id = NEW.asset_id 
                   AND portfolio_id = NEW.portfolio_id
                   AND currency = NEW.currency
                   ORDER BY DATE ASC  -- FIFO approach
        LOOP
            IF QUANTITY_CNT >= lot.quantity THEN
                TAX_BASE_COMP := TAX_BASE_COMP + lot.tax_base_amount;
                QUANTITY_CNT := QUANTITY_CNT - lot.quantity;
                DELETE FROM TAX_LOT WHERE id = lot.id;
            ELSE
                -- final, partial tax lot 
                TAX_BASE_COMP := TAX_BASE_COMP + ROUND(QUANTITY_CNT * lot.price, 2);
                UPDATE TAX_LOT SET 
                quantity = lot.quantity - QUANTITY_CNT,
                tax_base_amount = ROUND((lot.quantity - QUANTITY_CNT) * lot.price ,2)
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

        INSERT INTO ASSET_VALUATION (asset_id, date, currency, price)
        VALUES (
            v_asset_id,
            NEW.date,
            NEW.currency,
            NEW.price
        );
    ELSIF v_asset.id IS NOT NULL THEN
        INSERT INTO ASSET_VALUATION (asset_id, date, currency, price)
        VALUES (
            v_asset.id,
            NEW.date,
            NEW.currency,
            NEW.price
        );
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