import socket
import threading
import sqlite3
import pickle
import traceback
import os
import hashlib
import struct
import time
import random
from typing import Set, Dict
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import filedialog
import logging
import json
import shutil
PORT_PEER = 5500

PIECE_SIZE = 512 * 1024
FORMAT = 'utf-8'

REGISTER = 'register'
REGISTER_SUCCESS = 'register_success'
REGISTER_FAIL = 'register_fail'

LOGIN = 'login'
LOGIN_SUCCESS = 'login_success'
LOGIN_FAIL = 'login_fail'
LOGIN_WRONG_PASSWORD = 'login_wrong_password'
LOGIN_NOT_FOUND = 'login_not_found'

LOGOUT = 'logout'
LOGOUT_SUCCESS = 'logout_success'

PUBLISH = 'publish'
PUBLISH_SUCCESS = 'publish_success'
PUBLISH_FAIL = 'publish_fail'

FETCH = 'fetch'
FETCH_SUCCESS = 'fetch_success'
FETCH_FAIL = 'fetch_fail'

GET_FILES = 'get_files'
GET_FILES_SUCCESS = 'get_files_success'
GET_FILES_FAIL = 'get_files_fail'

GET_PIECE = 'get_piece'
GET_PIECE_SUCCESS = 'get_piece_success'
GET_PIECE_FAIL = 'get_piece_fail'

