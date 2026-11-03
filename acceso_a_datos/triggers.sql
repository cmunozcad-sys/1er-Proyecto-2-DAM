-- 1. AUTOMATIZACIÓN DE IMPORTES
CREATE OR REPLACE FUNCTION fn_recalcular_importe()
RETURNS TRIGGER AS $$
DECLARE
    v_id_pedido INTEGER;
    v_estado    VARCHAR(12);
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_id_pedido := OLD.id_pedido;
    ELSE
        v_id_pedido := NEW.id_pedido;
    END IF;

    -- Comprobar que el pedido está en borrador
    SELECT estado INTO v_estado FROM pedido WHERE id_pedido = v_id_pedido;
    IF v_estado <> 'BORRADOR' THEN
        RAISE EXCEPTION 'No se pueden modificar las líneas de un pedido %', v_estado;
    END IF;

    -- Recalcular el total con la suma de todas sus líneas
    UPDATE pedido
    SET total = COALESCE((SELECT SUM(cantidad * precio_unitario)
                          FROM linea_pedido
                          WHERE id_pedido = v_id_pedido), 0)
    WHERE id_pedido = v_id_pedido;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_importe ON linea_pedido;
CREATE TRIGGER trg_importe
AFTER INSERT OR UPDATE OR DELETE ON linea_pedido
FOR EACH ROW
EXECUTE FUNCTION fn_recalcular_importe();

-- 2. AUTOMATIZACIÓN DE EXISTENCIAS
CREATE OR REPLACE FUNCTION fn_gestionar_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = OLD.estado THEN
        RETURN NEW;
    END IF;

    -- Confirmar: BORRADOR -> CONFIRMADO
    IF OLD.estado = 'BORRADOR' AND NEW.estado = 'CONFIRMADO' THEN

        IF EXISTS (
            SELECT 1
            FROM (SELECT id_variante, talla, SUM(cantidad) AS pedidas
                  FROM linea_pedido
                  WHERE id_pedido = NEW.id_pedido
                  GROUP BY id_variante, talla) l
            JOIN stock s ON s.id_variante = l.id_variante AND s.talla = l.talla
            WHERE s.cantidad < l.pedidas
        ) THEN
            RAISE EXCEPTION 'Stock insuficiente para confirmar el pedido %', NEW.ref_odoo;
        END IF;

        -- Descontar el stock
        UPDATE stock s
        SET cantidad = s.cantidad - l.pedidas,
            ultima_actualizacion = now()
        FROM (SELECT id_variante, talla, SUM(cantidad) AS pedidas
              FROM linea_pedido
              WHERE id_pedido = NEW.id_pedido
              GROUP BY id_variante, talla) l
        WHERE s.id_variante = l.id_variante AND s.talla = l.talla;

        NEW.fecha_confirmacion := now();

    -- Cancelar: CONFIRMADO -> CANCELADO
    ELSIF OLD.estado = 'CONFIRMADO' AND NEW.estado = 'CANCELADO' THEN

        UPDATE stock s
        SET cantidad = s.cantidad + l.pedidas,
            ultima_actualizacion = now()
        FROM (SELECT id_variante, talla, SUM(cantidad) AS pedidas
              FROM linea_pedido
              WHERE id_pedido = NEW.id_pedido
              GROUP BY id_variante, talla) l
        WHERE s.id_variante = l.id_variante AND s.talla = l.talla;

        NEW.fecha_cancelacion := now();

    -- Cancelar: BORRADOR -> CANCELADO
    ELSIF OLD.estado = 'BORRADOR' AND NEW.estado = 'CANCELADO' THEN

        NEW.fecha_cancelacion := now();

    -- Cualquier otro cambio de estado
    ELSE
        RAISE EXCEPTION 'Cambio de estado no permitido: de % a %', OLD.estado, NEW.estado;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_stock ON pedido;
CREATE TRIGGER trg_stock
BEFORE UPDATE OF estado ON pedido
FOR EACH ROW
EXECUTE FUNCTION fn_gestionar_stock();

-- 3. AUDITORÍA
CREATE OR REPLACE FUNCTION fn_auditoria()
RETURNS TRIGGER AS $$
DECLARE
    v_id       INTEGER;
    v_accion   VARCHAR(50);
    v_resumen  JSONB;
    v_usuario  INTEGER;
BEGIN
    -- Usuario de la aplicación (NULL si no se ha indicado)
    v_usuario := NULLIF(current_setting('app.id_usuario', true), '')::INTEGER;

    IF TG_OP = 'INSERT' THEN
        v_accion  := 'ALTA';
        v_resumen := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_accion  := 'MODIFICACION';
        v_resumen := jsonb_build_object('antes', to_jsonb(OLD), 'despues', to_jsonb(NEW));
    ELSE
        v_accion  := 'BAJA';
        v_resumen := to_jsonb(OLD);
    END IF;

    -- Id del registro y acciones especiales de los pedidos
    IF TG_TABLE_NAME = 'pedido' THEN
        IF TG_OP = 'DELETE' THEN
            v_id := OLD.id_pedido;
        ELSE
            v_id := NEW.id_pedido;
        END IF;
        IF TG_OP = 'UPDATE' AND NEW.estado <> OLD.estado THEN
            v_accion := 'CAMBIO ESTADO: ' || NEW.estado;
        END IF;
    ELSE
        IF TG_OP = 'DELETE' THEN
            v_id := OLD.id_linea;
        ELSE
            v_id := NEW.id_linea;
        END IF;
    END IF;

    INSERT INTO log_eventos (tabla, operacion, registro_id, accion, resumen, id_usuario)
    VALUES (TG_TABLE_NAME, TG_OP, v_id, v_accion, v_resumen, v_usuario);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auditoria_ped ON pedido;
CREATE TRIGGER trg_auditoria_ped
AFTER INSERT OR DELETE
   OR UPDATE OF estado, id_cliente, fecha_entrega_prevista, observaciones
ON pedido
FOR EACH ROW
EXECUTE FUNCTION fn_auditoria();

DROP TRIGGER IF EXISTS trg_auditoria_lin ON linea_pedido;
CREATE TRIGGER trg_auditoria_lin
AFTER INSERT OR UPDATE OR DELETE ON linea_pedido
FOR EACH ROW
EXECUTE FUNCTION fn_auditoria();
