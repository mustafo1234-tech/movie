from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()


class GenreStates(StatesGroup):
    selecting = State()


class RandomStates(StatesGroup):
    selecting = State()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_search = State()
