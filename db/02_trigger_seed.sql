--TRIGGER FUNCTIONS
CREATE OR REPLACE FUNCTION fnc_calc_transaction_data() 
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    TAX_BRACKET tax_rate.rate%type;
    TRANSACTION_TYPE_CODE transaction_type.code%type;
    POSITION_QUANTITY position.quantity%type;
BEGIN
    SELECT rate INTO TAX_BRACKET 
    FROM TAX_RATE 
    WHERE ID = (SELECT tax_rate_id 
                FROM PORTFOLIO 
                WHERE id = NEW.portfolio_id);

    SELECT code INTO TRANSACTION_TYPE_CODE 
    FROM TRANSACTION_TYPE 
    WHERE ID = NEW.transaction_type_id;

    NEW.total_amount := (NEW.price * NEW.quantity) + NEW.fee;

    -- tax_amount in case of selling calculated and updated based on tax lots
    IF TRANSACTION_TYPE_CODE IN ('DIV', 'INT') AND TAX_BRACKET <> 0 THEN
        NEW.tax_amount := ROUND((NEW.price * NEW.quantity) * (TAX_BRACKET / 100));
    END IF;

    IF TRANSACTION_TYPE_CODE = 'SEL' THEN
        SELECT quantity INTO POSITION_QUANTITY
        FROM POSITION 
        WHERE portfolio_id = NEW.portfolio_id
        AND asset_id = NEW.asset_id;

        IF NEW.quantity > COALESCE(POSITION_QUANTITY, 0) THEN
        -- @TODO: add logging
            RAISE EXCEPTION 'Trying to sell % when overall holding is %', NEW.quantity, POSITION_QUANTITY;
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
    
    SELECT code INTO TRANSACTION_TYPE_CODE 
    FROM TRANSACTION_TYPE 
    WHERE ID = NEW.transaction_type_id;

    SELECT code INTO ASSET_TYPE_CODE
    FROM ASSET_TYPE
    WHERE ID = (SELECT asset_type_id FROM ASSET
                WHERE id = NEW.asset_id);

    -- @TODO: add booking matrix table to replace giant case here
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fnc_calc_position()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN

    WITH trans AS (
        SELECT 
            sum(CASE WHEN tt.code = 'SEL' THEN (-1) * t.quantity ELSE t.quantity END) AS sum_q, 
            sum(CASE WHEN tt.code = 'SEL' THEN (-1) * t.total_amount ELSE t.total_amount END) AS sum_t, 
            sum(t.fee) AS sum_f, 
            avg(CASE WHEN tt.code = 'BUY' THEN t.price END)::NUMERIC(20,4) AS avg_p, 
            count(1) AS cnt,
            NEW.asset_id AS asset_id,
            NEW.portfolio_id AS portfolio_id,
            NEW.currency AS currency
        FROM TRANSACTION t
        INNER JOIN TRANSACTION_TYPE tt
        ON t.transaction_type_id = tt.id
        WHERE 
            t.portfolio_id = NEW.portfolio_id
        AND t.asset_id = NEW.asset_id
        AND t.currency = NEW.currency
        AND tt.code IN ('BUY', 'SEL')
    )
    MERGE INTO POSITION p
    USING trans t 
    ON t.asset_id = p.asset_id
    AND t.portfolio_id = p.portfolio_id
    WHEN NOT MATCHED THEN
        INSERT (portfolio_id, asset_id, currency, quantity, average_price, fee, total_amount)
        VALUES (t.portfolio_id, t.asset_id, t.currency, t.sum_q, t.avg_p, t.sum_f, t.sum_t)
    WHEN MATCHED AND t.cnt = 1 THEN
        UPDATE SET 
            quantity = t.sum_q, 
            average_price = t.avg_p, 
            fee = t.sum_f, 
            total_amount = t.sum_t
    WHEN MATCHED AND t.cnt > 1 AND t.sum_q = 0 THEN
        DELETE 
    WHEN MATCHED AND t.cnt > 1 AND t.sum_q > 0 THEN
        UPDATE SET 
            quantity = t.sum_q, 
            average_price = t.avg_p, 
            fee = t.sum_f, 
            total_amount = t.sum_t;

    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION fnc_calc_tax_lot()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $$
BEGIN
    -- @TODO: add tax lot logic here
    -- update the transaction tax amount in case of selling based on the tax lots
    -- tax on DIV and INT calculated directly in transaction trigger
    RETURN NEW;
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

CREATE OR REPLACE TRIGGER trg_calc_position
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_position();


CREATE OR REPLACE TRIGGER trg_calc_tax_lot()
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_calc_tax_lot();