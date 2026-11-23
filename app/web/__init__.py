# -*- coding: utf-8 -*-
"""Web View layer. """
from flask import Blueprint

bp = Blueprint('web', __name__, template_folder='templates')

from app.web import routes  # noqa: E402,F401