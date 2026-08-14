create table if not exists event_orders (
    event_id varchar(64) primary key,
    order_id varchar(64) not null,
    amount numeric(12,2) not null,
    ts timestamp not null,
    create_at timestamp not null default current_timestamp
);