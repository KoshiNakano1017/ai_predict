-- 10_要件定義書.md §3.1.2 / F-15 トライアル自動降格
-- plan='trial' かつ trial_ends_at <= now() のユーザーを 'expired' に更新する関数。
--
-- 運用方法（いずれか1つを採用）:
--   1) Supabase Dashboard → Database → Cron で
--      `select 0 0 * * * $$ select public.expire_trial_users(); $$;` を毎日 0:00 に登録
--   2) Windowsバッチ側から `supabase.rpc('expire_trial_users')` を日次で呼び出す
--   3) 緊急時は Supabase SQL Editor から `select public.expire_trial_users();` を手動実行

create or replace function public.expire_trial_users()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  affected integer;
begin
  update public.users
     set plan = 'expired'
   where plan = 'trial'
     and trial_ends_at is not null
     and trial_ends_at <= now();

  get diagnostics affected = row_count;
  return affected;
end;
$$;

-- 関数は service_role からのみ呼び出せるようにする
revoke all on function public.expire_trial_users() from public;
revoke all on function public.expire_trial_users() from anon;
revoke all on function public.expire_trial_users() from authenticated;
grant execute on function public.expire_trial_users() to service_role;
