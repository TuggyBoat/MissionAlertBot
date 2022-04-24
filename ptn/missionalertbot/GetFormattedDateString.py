from datetime import datetime
from datetime import timezone
from dateutil.relativedelta import relativedelta

# get date and time
def get_formatted_date_string():
    """
    Returns a tuple of the Elite Dangerous Time and the current real world time.

    :rtype: tuple
    """
    dt_now = datetime.now(tz=timezone.utc)
    # elite_time_string is the Elite Dangerous time this is running in, today plus 1286 years
    elite_time_string = (dt_now + relativedelta(years=1286)).strftime("%d %B %Y %H:%M %Z")
    current_time_string = dt_now.strftime("%Y%m%d %H%M%S")
    return elite_time_string, current_time_string