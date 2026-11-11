ALTER TABLE pedido
    ADD COLUMN estado_odoo VARCHAR(12) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado_odoo IN ('PENDIENTE', 'SINCRONIZADO', 'ERROR')),
    ADD COLUMN odoo_id INTEGER,
    ADD COLUMN error_odoo VARCHAR(300),
    ADD COLUMN intentos_odoo INTEGER NOT NULL DEFAULT 0;

UPDATE pedido SET estado_odoo = 'SINCRONIZADO';

CREATE INDEX idx_pedido_estado_odoo ON pedido(estado, estado_odoo);
