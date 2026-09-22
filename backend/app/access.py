"""One access decision shared by operational endpoints and session destinations."""
from .models import now
from .commercial_models import Subscription


def business_access(db, business):
    if business.access_blocked:
        return {'allowed':False,'state':'blocked'}
    subscription=db.get(Subscription,business.id)
    if subscription and subscription.status=='active' and subscription.valid_until>now():
        return {'allowed':True,'state':'subscribed'}
    if business.legacy_access:
        return {'allowed':True,'state':'legacy_review'}
    if business.trial_started_at and business.trial_started_at<=now() and business.trial_ends_at>now():
        return {'allowed':True,'state':'trial'}
    return {'allowed':False,'state':'payment_required'}
