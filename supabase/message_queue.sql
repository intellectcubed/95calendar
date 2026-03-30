create table message_queue (
  id bigserial primary key,
  source_message_id text not null,      -- GroupMe message id
  sender_id text not null,
  payload jsonb not null,
  status text not null default 'PENDING', -- PENDING | PROCESSING | DONE | FAILED
  workflow_id text,
  created_at timestamptz default now(),
  locked_at timestamptz
);

create index on message_queue (status, created_at);
