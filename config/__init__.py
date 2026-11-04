import pymysql

pymysql.install_as_MySQLdb()

# Bypass MariaDB version check & RETURNING feature for XAMPP (MariaDB 10.4)
from django.db.backends.mysql.base import DatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures

DatabaseWrapper.check_database_version_supported = lambda self: None
DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)
DatabaseFeatures.can_return_rows_from_update = property(lambda self: False)
