#!/bin/bash
export FLASK_APP=ledger.py
flask run --host=0.0.0.0 --port=$PORT

