-- 03_認可設計.md §7 データモデル に基づく users テーブル
-- Supabase Dashboard > SQL Editor で実行する

-- 1. users テーブル
create table if not exists public.users (
  id uuid references auth.users on delete cascade primary key,
  plan text not null default 'trial'
    check (plan in ('trial', 'expired', 'pro')),
  stripe_customer_id text,
  stripe_subscription_id text,
  trial_ends_at timestamptz default (now() + interval '7 days'),
  created_at timestamptz default now()
);

-- 2. RLS を有効化
alter table public.users enable row level security;

-- 3. RLS ポリシー: ユーザーは自分のレコードのみ読み取り可
create policy "users_select_own"
  on public.users for select
  using (auth.uid() = id);

-- 4. RLS ポリシー: ユーザーは自分のレコードのみ更新可（plan は Webhook 経由のみ更新想定だが安全弁として）
create policy "users_update_own"
  on public.users for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- 5. service_role は RLS をバイパスするため、Webhook からの更新は制約なし

-- 6. Auth ユーザー作成時に自動で users レコードを作る trigger
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, plan, trial_ends_at)
  values (new.id, 'trial', now() + interval '7 days');
  return new;
end;
$$;

-- 既存の trigger があれば削除してから作り直す
drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
