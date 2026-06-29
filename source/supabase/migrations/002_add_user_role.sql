-- users テーブルへ role を追加して権限制御を可能にする
alter table public.users
  add column if not exists role text not null default 'member'
  check (role in ('member', 'admin'));

-- 既存ユーザーの role を補完
update public.users
set role = 'member'
where role is null;

-- クライアントからの users 更新を禁止し、権限昇格を防ぐ
drop policy if exists "users_update_own" on public.users;

-- Auth ユーザー作成時の初期 role を明示
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, plan, role, trial_ends_at)
  values (new.id, 'trial', 'member', now() + interval '7 days');
  return new;
end;
$$;
