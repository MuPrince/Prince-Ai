import os
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent / "tmp_data"
os.environ["PRINCE_PA_DATA_DIR"] = str(TEST_DATA_DIR)

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

settings.data_dir = TEST_DATA_DIR


@pytest.fixture()
def client():
    return TestClient(app)
