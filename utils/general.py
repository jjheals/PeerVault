from flask import Request


def filter_args(expected_args:dict[str,type], request:Request) -> dict: 
    """Filters the args given in the request to only those in expected_args, adjusts types as appropriate 
    and possible, and returns the result."""
    
    # Get the args given in the request
    given_args:dict[str,str] = {
        a: request.args.get(a, None) 
        for a in expected_args.keys()
    }
            
    # Check the given args types and make sure they are what we expect
    for given_arg, given_val in given_args.items(): 
        
        # If given_val is empty, do nothing 
        if given_val == None or given_val == '': continue
        
        # Convert the value to its expected type if possible
        try:
            # Check int
            if expected_args[given_arg] == int:
                given_args[given_arg] = int(given_val)
            # Check str 
            elif expected_args[given_arg] == str:
                given_args[given_arg] = str(given_val).strip() 
            
         # If conversion fails, ignore this argument   
        except ValueError: given_args[given_arg] = None  
        
        # Given an invalid argument
        except KeyError: given_args[given_arg] = None  
                
    # Fix the "online" arg to be "true" or "false" 
    if given_args.get('online') in (0, 1):  
        given_args['online'] = bool(given_args['online'])
    else:
        given_args['online'] = None 
    
    # Return the adjusted given_args dict
    return given_args