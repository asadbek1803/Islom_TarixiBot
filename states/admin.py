from aiogram.fsm.state import StatesGroup, State



class AdminState(StatesGroup):
    
    
    # New states for admin management
    add_admin_id = State()
    
    # States for film management
    film_name = State()
    film_code = State()
    film_series = State()
    film_channel = State()
    
    # States for client management
    client_phone = State()
    client_api_id = State()
    client_api_hash = State()
    client_session = State()
    client_code = State()         # For OTP code
    client_2fa = State() 