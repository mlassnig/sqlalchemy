"""Support for the PostgreSQL database via the pg8000 driver.

Connecting
----------

URLs are of the form
`postgresql+pg8000://user:password@host:port/dbname[?key=value&key=value...]`.

Unicode
-------

pg8000 requires that the postgresql client encoding be configured in the postgresql.conf file
in order to use encodings other than ascii.  Set this value to the same value as 
the "encoding" parameter on create_engine(), usually "utf-8".

Interval
--------

Passing data from/to the Interval type is not supported as of yet.

"""
import decimal

from sqlalchemy.engine import default
from sqlalchemy import util, exc
from sqlalchemy import processors
from sqlalchemy import types as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect, \
                PGCompiler, PGIdentifierPreparer, PGExecutionContext

class _PGNumeric(sqltypes.Numeric):
    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            if coltype in (700, 701):
                return processors.to_decimal_processor_factory(decimal.Decimal)
            elif coltype == 1700:
                # pg8000 returns Decimal natively for 1700
                return None
            else:
                raise exc.InvalidRequestError("Unknown PG numeric type: %d" % coltype)
        else:
            if coltype in (700, 701):
                # pg8000 returns float natively for 701
                return None
            elif coltype == 1700:
                return processors.to_float
            else:
                raise exc.InvalidRequestError("Unknown PG numeric type: %d" % coltype)

class PGExecutionContext_pg8000(PGExecutionContext):
    pass


class PGCompiler_pg8000(PGCompiler):
    def visit_mod(self, binary, **kw):
        return self.process(binary.left) + " %% " + self.process(binary.right)

    def post_process_text(self, text):
        if '%%' in text:
            util.warn("The SQLAlchemy postgresql dialect now automatically escapes '%' in text() "
                      "expressions to '%%'.")
        return text.replace('%', '%%')


class PGIdentifierPreparer_pg8000(PGIdentifierPreparer):
    def _escape_identifier(self, value):
        value = value.replace(self.escape_quote, self.escape_to_quote)
        return value.replace('%', '%%')

    
class PGDialect_pg8000(PGDialect):
    driver = 'pg8000'

    supports_unicode_statements = True
    
    supports_unicode_binds = True
    
    default_paramstyle = 'format'
    supports_sane_multi_rowcount = False
    execution_ctx_cls = PGExecutionContext_pg8000
    statement_compiler = PGCompiler_pg8000
    preparer = PGIdentifierPreparer_pg8000
    
    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.Numeric : _PGNumeric,
        }
    )
    
    @classmethod
    def dbapi(cls):
        return __import__('pg8000').dbapi

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e):
        return "connection is closed" in str(e)

dialect = PGDialect_pg8000