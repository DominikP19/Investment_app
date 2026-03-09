--TRIGGER FUNCTIONS
CREATE OR REPLACE FUNCTION fnc_process_transaction_data() 
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

    IF TRANSACTION_TYPE_CODE IN ('SEL', 'DIV', 'INT') AND TAX_BRACKET <> 0 THEN
        NEW.tax_amount := ROUND((NEW.price * NEW.quantity) * (TAX_BRACKET / 100));
    END IF;

    IF TRANSACTION_TYPE_CODE = 'SEL' THEN
        SELECT quantity INTO POSITION_QUANTITY
        FROM POSITION 
        WHERE portfolio_id = NEW.portfolio_id
        AND asset_id = NEW.asset_id;

        IF NEW.quantity > NVL(POSITION_QUANTITY, 0) THEN
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

CREATE OR REPLACE FUNCTION fnc_update_position()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    -- @TODO: Implement position update logic
    RETURN NEW;
END;
$$;

-- TRIGGERS
CREATE OR REPLACE TRIGGER trg_transaction_calc 
BEFORE INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_process_transaction_data();

CREATE OR REPLACE TRIGGER trg_booking
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_create_booking();

CREATE OR REPLACE TRIGGER trg_position_update
AFTER INSERT OR UPDATE ON TRANSACTION
FOR EACH ROW
EXECUTE FUNCTION fnc_update_position();