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
from typing import Set, Dict, DefaultDict
from collections import defaultdict
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import filedialog
import logging
import json
import shutil

# Network Constants
PIECE_SIZE = 512 * 1024  # 512KB per piece
BLOCK_SIZE = 16384       # 16KB per block
MAX_CONNECTIONS = 5
MAX_PENDING_REQUESTS = 10
KEEP_ALIVE_INTERVAL = 120  # 2 minutes

# Message Types - Authentication
REGISTER = 'register'
REGISTER_SUCCESS = 'register_success'
REGISTER_FAIL = 'register_fail'
LOGIN = 'login'
LOGIN_SUCCESS = 'login_success'
LOGIN_FAIL = 'login_fail'
LOGOUT = 'logout'

# Message Types - File Operations
PUBLISH = 'publish'
PUBLISH_SUCCESS = 'publish_success'
FETCH = 'fetch'
FETCH_SUCCESS = 'fetch_success'
GET_FILES = 'get_files'
GET_FILES_SUCCESS = 'get_files_success'

# Message Types - Piece Transfer
HANDSHAKE = 'handshake'
BITFIELD = 'bitfield'
REQUEST = 'request'
PIECE = 'piece'
HAVE = 'have'
INTERESTED = 'interested'
NOT_INTERESTED = 'not_interested'
CHOKE = 'choke'
UNCHOKE = 'unchoke'
CANCEL = 'cancel'

# Message Types - Piece Status
UPDATE_BITFIELD = 'update_bitfield'
PIECE_STATUS = 'piece_status'

# Transfer States
DOWNLOADING = 'downloading'
UPLOADING = 'uploading'
COMPLETED = 'completed'
FAILED = 'failed'