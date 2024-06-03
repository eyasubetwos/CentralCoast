from apscheduler.schedulers.background import BackgroundScheduler
from src.api.barrels import purchase_barrels_if_needed

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(purchase_barrels_if_needed, 'interval', hours=2)
    scheduler.start()
