"""Operator-only maintenance. Run on the server, never from the public frontend."""
import argparse
import os
import time
import pyotp
try:
    from . import accounts
except ImportError:
    import accounts

parser=argparse.ArgumentParser(description='HealthUp account maintenance')
parser.add_argument('action',choices=['cleanup','enroll-staff','revoke-staff'])
parser.add_argument('--email')
args=parser.parse_args()
accounts.require_enabled()
with accounts.database() as db:
    if args.action=='cleanup':
        now=int(time.time())
        db.execute('DELETE FROM sessions WHERE expires<?',(now,))
        db.execute('DELETE FROM tokens WHERE expires<? OR used=1',(now,))
        db.execute('DELETE FROM limits WHERE start<?',(now-3600,))
        db.execute('DELETE FROM audits WHERE created<?',(now-90*86400,))
        db.execute('DELETE FROM requests WHERE status IN ("completed","denied") AND created<?',(now-90*86400,))
        db.execute('DELETE FROM webhooks WHERE created<?',(now-90*86400,))
        print('Expired operational records purged. Review infrastructure backup retention separately.')
    else:
        if not args.email:parser.error('--email is required')
        user=db.execute('SELECT * FROM users WHERE email_idx=? AND verified=1',(accounts.identity(args.email),)).fetchone()
        if not user:raise SystemExit('A verified account is required.')
        db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        if args.action=='revoke-staff':
            db.execute('UPDATE users SET role="member",mfa_enc=NULL,last_totp=-1 WHERE id=?',(user['id'],))
            accounts.audit(db,'operator','staff_revoked')
            print('Staff access revoked.')
        else:
            secret=os.getenv('STAFF_ENROLLMENT_SECRET')
            if not secret or len(secret)<32:raise SystemExit('Set STAFF_ENROLLMENT_SECRET to a securely generated Base32 TOTP secret of at least 32 characters. Enroll it privately in the staff authenticator; do not commit it.')
            pyotp.TOTP(secret).now()
            db.execute('UPDATE users SET role="staff",mfa_enc=?,last_totp=-1 WHERE id=?',(accounts.encrypt(secret),user['id']))
            accounts.audit(db,'operator','staff_enrolled')
            print('Staff MFA enrolled. No seed was printed. Remove the enrollment environment variable after use.')
