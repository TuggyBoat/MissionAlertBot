"""
Module to return formatted date strings.

Depends on: none
"""

# import libraries
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta


# get date and time
def get_formatted_date_string():
    print("Called get_formattted_date_string")
    """
    Returns a tuple of the Elite Dangerous Time and the current real world time.

    :rtype: tuple
    """
    dt_now = datetime.now(tz=timezone.utc)
    # elite_time_string is the current time as reported by Elite Dangerous, UTC plus 1286 years
    elite_time_string = (dt_now + relativedelta(years=1286)).strftime("%d %B %Y %H:%M %Z")
    print(f"Elite time string: {elite_time_string}")
    current_time_string = dt_now.strftime("%Y%m%d_%H%M%S")
    print(f"Current time string: {current_time_string}")
    return elite_time_string, current_time_string