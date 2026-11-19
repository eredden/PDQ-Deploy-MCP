# main.py - The PDQ Deploy MCP server.

from __future__ import annotations
from contextlib import contextmanager
from mcp.server import MCPServer

import os
import sqlite3

MCP_SERVER = MCPServer("PDQ Deploy")
DB_PATH = os.getenv("PDQ_DEPLOY_DB")


@contextmanager
def get_db_cursor():
    """Open a short-lived, read-only connection and yields a cursor."""

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"{DB_PATH} not found.")

    # The mode=ro flag forces the file to open in Read Only (RO) mode.
    db_uri = f"file:///{DB_PATH}?mode=ro"

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
    limit: int = 50,
) -> list[dict]:
    """Get deployment history filtered by optional package_id and ISO date range (YYYY-MM-DD)."""

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
    params.append(limit)

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

        return [dict(row) for row in cursor.fetchall()]

    
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

        # We convert the list of sqlite3.Row objects into a list of dict objects.
        return [dict(row) for row in cursor.fetchall()]

    
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

        return [dict(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()    
def get_package_steps(package_id: int) -> list[dict]:
    """Get ordered execution steps for a specific package."""

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

        return [dict(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def get_tables() -> list[str]:
    """Get a list of all the database tables."""

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
        cursor.execute(f"PRAGMA table_info({table_name});")

        return [dict(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def get_target_lists(target_list_id: int | None = None) -> list[dict]:
    """Get all Target Lists or the specific computer targets inside a given target_list_id."""

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

        return [dict(row) for row in cursor.fetchall()]


@MCP_SERVER.tool()
def run_read_only_query(sql: str, max_rows: int = 100) -> list[dict]:
    """
    Execute a custom read-only SELECT or WITH query for questions not covered by standard tools.
    Results are capped to 100 rows by default. Change the value of max_rows to bypass this.
    """

    cleaned = sql.strip()

    # Even more defense-in-depth paranoia. This is the third layer of 
    # code intended to prevent writes to the SQLite database.
    if not cleaned.upper().startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT or WITH queries are permitted.")

    with get_db_cursor() as cursor:
        cursor.execute(cleaned)

        return [dict(row) for row in cursor.fetchmany(max_rows)]


if __name__ == "__main__":
    if not DB_PATH or not os.path.exists(DB_PATH):
        raise ValueError("The PDQ_DEPLOY_DB environment variable must point to a PDQ Deploy SQLite database.")

    MCP_SERVER.run(transport="stdio")
