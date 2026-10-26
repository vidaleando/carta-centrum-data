from tests.conftest import make_settings

NEON_STYLE_URL = "postgresql://user:s3cret@ep-x.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


def test_dsn_drops_libpq_only_params_and_keeps_sslmode():
    dsn = make_settings(database_url=NEON_STYLE_URL).asyncpg_dsn
    assert "channel_binding" not in dsn
    assert dsn.endswith("/neondb?sslmode=require")


def test_database_label_has_no_credentials():
    label = make_settings(database_url=NEON_STYLE_URL).database_label
    assert label == "ep-x.eu-west-2.aws.neon.tech/neondb"


def test_cors_origins_parsing():
    assert make_settings(cors_origins="").cors_origin_list == []
    assert make_settings(cors_origins="https://a.example, https://b.example").cors_origin_list == [
        "https://a.example", "https://b.example",
    ]
