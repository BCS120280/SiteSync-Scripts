def time_elapsed_since_date(date_str):
	
    lastSeen = system.date.parse(date_str, 'yyyy-MM-dd h:m:s a')

    now = system.date.now()

    total_minutes = system.date.minutesBetween(lastSeen, now)

    result = ""
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60
    if days > 0:
    	if days == 1:
    		result += str(days) + " day "
    	else:	
        	result += str(days) + " days, "
    if hours > 0:
    	if hours == 1:
    		result += str(hours) + " hour, "
    	else:
        	result += str(hours) + " hours, "
    if minutes > 0:
    	if minutes == 1:
    	
        	result += str(minutes) + " minute"
        else:
        	result += str(minutes) + " minutes"
    if result == "":
        result = "just now"
    else:	
    	result += " ago"

    return result
	    
	    
def timestampLastSeen(lastSeen):
	
    now = system.date.now()
    lastSeen = system.date.fromMillis(lastSeen*1000)

    total_minutes = system.date.minutesBetween(lastSeen, now)

    result = ""
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60
    if days > 0:
    	if days == 1:
    		result += str(days) + " day "
    	else:	
        	result += str(days) + " days, "
    if hours > 0:
    	if hours == 1:
    		result += str(hours) + " hour, "
    	else:
        	result += str(hours) + " hours, "
    if minutes > 0:
    	if minutes == 1:
    	
        	result += str(minutes) + " minute"
        else:
        	result += str(minutes) + " minutes"
    if result == "":
        result = "just now"
    else:	
    	result += " ago"

    return result
	    
	    
	    
	    
	    
def time_elapsed_since_dateTag(lastSeen):
		
	if system.date.getYear(lastSeen) > 2023:    
	
	    now = system.date.now()
	
	    total_minutes = system.date.minutesBetween(lastSeen, now)
	
	    result = ""
	    days = total_minutes // (24 * 60)
	    hours = (total_minutes % (24 * 60)) // 60
	    minutes = total_minutes % 60
	    if days > 0:
	    	if days == 1:
	    		result += str(days) + " day "
	    	else:	
	        	result += str(days) + " days, "
	    if hours > 0:
	    	if hours == 1:
	    		result += str(hours) + " hour, "
	    	else:
	        	result += str(hours) + " hours, "
	    if minutes > 0:
	    	if minutes == 1:
	    	
	        	result += str(minutes) + " minute"
	        else:
	        	result += str(minutes) + " minutes"
	    if result == "":
	        result = "just now"
	    else:	
	    	result += " ago"
	
	    return result
	else:
		return "Never seen"