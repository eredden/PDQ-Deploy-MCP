# server.py - The PDQ Deploy MCP server.

from __future__ import annotations

from argparse import ArgumentParser
from contextlib import contextmanager
from mcp.server import MCPServer
from pathlib import Path

import sqlite3

MCP_SERVER = MCPServer("PDQ Deploy")
DB_PATH: Path = None

@contextmanager
def get_db_cursor():
    """Open a short-lived, read-only connection and yields a cursor."""

    if DB_PATH is None or not DB_PATH.is_file():
        raise FileNotFoundError(f"{DB_PATH} not found.")

    # The mode=ro flag forces the file to open in Read Only (RO) mode.
    db_uri = f"{Path(DB_PATH).resolve().as_uri()}?mode=ro"

    conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row # Replaces tuple rows with dict rows.

    try:
        # Switching query_only to ON defends against writes on the SQLite level.
        # This is technically redundant since the RO flag for the file URI should 
        # block writes anyways, but I am paranoid. Aaaaaaaaaaaaah!
        cursor = conn.cursor()
        cursor.execute("PRAGMA query_only = ON;")

        yield cursor

    finally:
        # Ensures the connection and any read locks are closed immediately.
        conn.close()


@MCP_SERVER.tool()
def get_deployments(
    package_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    max_rows: int = 100,
) -> list[dict]:
    """Get deployment history filtered by optional package_id and ISO date range (YYYY-MM-DD)."""

    if max_rows < 1:
            raise ValueError("max_rows must be greater than or equal to 1.")

    conditions = []
    params = []

    if package_id is not None:
        conditions.append("d.PackageId = ?")
        params.append(package_id)

    if start_date:
        conditions.append("d.Started >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("d.Started <= ?")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(max_rows)

    # UserName is the user performing the PDQ job on the hosts,
    # while DeployConsoleUser is the person who started the job.
    query = f"""
        SELECT
            d.DeploymentId,
            d.PackageId,
            p.Name AS PackageName,
            d.Started,
            d.Finished,
            d.Status,
            d.UserName,
            d.DeployConsoleUser,
            COUNT(dc.DeploymentComputerId) AS TotalTargets
        FROM Deployments d
        LEFT JOIN Packages p ON d.PackageId = p.PackageId
        LEFT JOIN DeploymentComputers dc ON d.DeploymentId = dc.DeploymentId
        {where_clause}
        GROUP BY d.DeploymentId
        ORDER BY d.Started DESC
        LIMIT ?;
    """

    with get_db_cursor() as cursor:
        cursor.execute(query, tuple(params))

        return [_sanitize_row(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def get_deployment_failures(
    start_date: str | None = None,
    end_date: str | None = None,
    package_id: int | None = None,
    max_rows: int = 100
) -> list[dict]:
    """Get the latest failed deployment targets filtered by date range and optional package_id."""

    if max_rows < 1:
        raise ValueError("max_rows must be greater than or equal to 1.")

    conditions = [
        """(
            COALESCE(dc.Error, '') <> ''
            OR LOWER(COALESCE(dc.Status, '')) LIKE '%fail%'
            OR LOWER(COALESCE(dc.Stage, '')) LIKE '%fail%'
        )"""
    ]
    params = []

    if start_date:
        conditions.append("d.Started >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("d.Started <= ?")
        params.append(end_date)

    if package_id is not None:
        conditions.append("d.PackageId = ?")
        params.append(package_id)

    params.append(max_rows)
    query = f"""
        SELECT
            dc.DeploymentId,
            d.PackageId,
            d.PackageName,
            d.Started,
            dc.Name,
            dc.Status,
            dc.Error,
            dc.Stage,
            dc.Ended
        FROM DeploymentComputers dc
        JOIN Deployments d ON d.DeploymentId = dc.DeploymentId
        WHERE {' AND '.join(conditions)}
        ORDER BY d.Started DESC, dc.DeploymentComputerId DESC
        LIMIT ?;
    """

    with get_db_cursor() as cursor:
        cursor.execute(query, tuple(params))

        return [_sanitize_row(row) for row in cursor.fetchall()]

    
@MCP_SERVER.tool()
def get_packages(search: str | None = None) -> list[dict]:
    """Get PDQ packages optionally filtered by a case-insensitive name substring."""

    with get_db_cursor() as cursor:
        if search:
            cursor.execute(
                """
                SELECT PackageId, Name, Version, Description, Path, Created, Modified
                FROM Packages
                WHERE Name LIKE ?
                ORDER BY Name;
                """,
                (f"%{search}%",) # Wildcard for name filtering.
            )
            
        else:
            cursor.execute(
                """
                SELECT PackageId, Name, Version, Description, Path, Created, Modified 
                FROM Packages
                ORDER BY Name;
                """
            )

        return [_sanitize_row(row) for row in cursor.fetchall()]

    
@MCP_SERVER.tool()
def get_package_schedules(package_id: int | None = None) -> list[dict]:
    """Get all schedules along with their assigned packages. Optionally filter by package_id."""

    query = """
        SELECT
            s.ScheduleId,
            s.Name AS ScheduleName,
            s.IsEnabled,
            s.LastError,
            s.LastRun,
            p.PackageId,
            p.Name AS PackageName
        FROM Schedules s
        LEFT JOIN SchedulePackages sp ON s.ScheduleId = sp.ScheduleId
        LEFT JOIN Packages p ON sp.LocalPackageId = p.PackageId
    """

    params = ()

    if package_id is not None:
        query += " WHERE p.PackageId = ?"
        params = (package_id,)

    # This isn't immediately in the query because we don't want to order
    # all of the rows if we aren't going to use them all in the first place.
    # That's why we add the WHERE p.PackageId = ? filter first.
    query += " ORDER BY s.Name, p.Name;"

    with get_db_cursor() as cursor:
        cursor.execute(query, params)

        return [_sanitize_row(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()    
def get_package_steps(package_id: int) -> list[dict]:
    """Get the sequence of steps for a specific package."""

    query = """
        SELECT
            ps.PackageStepId,
            ps.Sequence,
            ps.Title,
            ps.IsEnabled,
            ps.ErrorMode
        FROM Packages p
        JOIN PackageSteps ps ON p.PackageDefinitionId = ps.PackageDefinitionId
        WHERE p.PackageId = ?
        ORDER BY ps.Sequence;
    """

    with get_db_cursor() as cursor:
        cursor.execute(query, (package_id,))

        return [_sanitize_row(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def get_tables() -> list[str]:
    """Get a list of all the database tables excluding SQLite system tables."""

    # We use sqlite_master as the master table since PDQ Deploy and Inventory use an older version
    # of SQLite. Newer versions of SQLite use the sqlite_schema table instead.
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        results = [item[0] for item in cursor.fetchall()]
    
        return results


@MCP_SERVER.tool()
def get_table_schema(table_name: str) -> list[dict]:
    """Get column names and types for a specific table."""

    valid_tables = get_tables()

    if table_name not in valid_tables:
        raise ValueError(f"Unknown table: {table_name}")

    with get_db_cursor() as cursor:    
        cursor.execute(f"PRAGMA table_info(\"{table_name}\");")

        return [_sanitize_row(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def get_target_lists(target_list_id: int | None = None) -> list[dict]:
    """Get all target lists or the specific computer targets inside a given target_list_id."""

    with get_db_cursor() as cursor:
        if target_list_id is None:
            cursor.execute(
                """
                SELECT tl.TargetListId, tl.Name, tl.Description, COUNT(t.TargetId) AS TargetCount
                FROM TargetLists tl
                LEFT JOIN Targets t ON tl.TargetListId = t.TargetListId
                GROUP BY tl.TargetListId
                ORDER BY tl.Name;
                """
            )

        else:
            cursor.execute(
                """
                SELECT t.TargetId, t.TargetListId, tl.Name AS ListName, t.Name AS TargetName
                FROM Targets t
                JOIN TargetLists tl ON t.TargetListId = tl.TargetListId
                WHERE t.TargetListId = ?
                ORDER BY t.Name;
                """,
                (target_list_id,),
            )

        return [_sanitize_row(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def run_read_only_query(sql: str, max_rows: int = 100) -> list[dict]:
    """
    Execute a custom read-only SELECT or WITH query for questions not covered by standard tools.
    Results are capped to 100 rows by default. Change the value of max_rows to bypass this.
    Note that leading comments will cause this function to reject the query, so please avoid them.
    """

    if max_rows < 1:
        raise ValueError("max_rows must be greater than or equal to 1.")

    cleaned = sql.strip()

    # Even more defense-in-depth paranoia. This is the third layer of 
    # code intended to prevent writes to the SQLite database.
    if not cleaned.upper().startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT or WITH queries are permitted.")

    with get_db_cursor() as cursor:
        cursor.execute(cleaned)

        return [_sanitize_row(row) for row in cursor.fetchmany(max_rows)]


def _sanitize_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row object into a sanitized dictionary."""

    serialized = {}

    for key in row.keys():
        value = row[key]

        # Omit blobs entirely to prevent excessive token usage and to 
        # avoid sending binary data as JSON over the MCP protocol.
        if isinstance(value, bytes):
            serialized[key] = f"<BLOB: {len(value)} BYTES OMITTED>"

        else:
            serialized[key] = value

    return serialized


def main() -> None:
    global DB_PATH

    parser = ArgumentParser(
        prog="PDQ Deploy MCP Server",
        description="An MCP server for read-only access to the PDQ Deploy database."
    )

    parser.add_argument(
        "--db-path",
        "--db",
        dest="db_path",
        required=True,
        type=str,
        help="Path to the SQLite database used by the server."
    )

    args = parser.parse_args()

    DB_PATH = Path(args.db_path).expanduser() if args.db_path else None

    if DB_PATH is None or not DB_PATH.is_file():
        raise ValueError("You must supply the PDQ Deploy SQLite database path with the --db-path argument.")

    MCP_SERVER.run(transport="stdio")


if __name__ == "__main__":
    main()
