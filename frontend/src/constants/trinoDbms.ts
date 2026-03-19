export interface TrinoDbmsOption {
  value: string;
  label: string;
  jdbcExample: string;
}

// This form only supports connectors configured with URL/user/password.
export const TRINO_DBMS_OPTIONS: TrinoDbmsOption[] = [
  {
    value: "clickhouse",
    label: "ClickHouse",
    jdbcExample: "jdbc:clickhouse://host:8123/database",
  },
  {
    value: "druid",
    label: "Apache Druid",
    jdbcExample:
      "jdbc:avatica:remote:url=http://host:8888/druid/v2/sql/avatica/",
  },
  {
    value: "duckdb",
    label: "DuckDB",
    jdbcExample: "jdbc:duckdb:/data/example.duckdb",
  },
  { value: "exasol", label: "Exasol", jdbcExample: "jdbc:exa:host:8563" },
  {
    value: "mariadb",
    label: "MariaDB",
    jdbcExample: "jdbc:mariadb://host:3306/database",
  },
  {
    value: "mysql",
    label: "MySQL",
    jdbcExample: "jdbc:mysql://host:3306/database",
  },
  {
    value: "oracle",
    label: "Oracle",
    jdbcExample: "jdbc:oracle:thin:@//host:1521/service",
  },
  {
    value: "postgresql",
    label: "PostgreSQL",
    jdbcExample: "jdbc:postgresql://host:5432/database",
  },
  {
    value: "redshift",
    label: "Amazon Redshift",
    jdbcExample: "jdbc:redshift://host:5439/database",
  },
  {
    value: "singlestore",
    label: "SingleStore",
    jdbcExample: "jdbc:singlestore://host:3306/database",
  },
  {
    value: "sqlserver",
    label: "SQL Server",
    jdbcExample: "jdbc:sqlserver://host:1433;databaseName=database",
  },
  {
    value: "vertica",
    label: "Vertica",
    jdbcExample: "jdbc:vertica://host:5433/database",
  },
];

const optionMap = new Map(
  TRINO_DBMS_OPTIONS.map((option) => [option.value, option]),
);

export function isKnownTrinoDbms(value: string | null | undefined): boolean {
  if (!value) return false;
  return optionMap.has(value);
}

export function getTrinoDbmsLabel(value: string | null | undefined): string {
  if (!value) return "";
  return optionMap.get(value)?.label ?? value;
}

export function getTrinoDbmsJdbcExample(
  value: string | null | undefined,
): string {
  if (!value) return "jdbc:postgresql://host:5432/database";
  return (
    optionMap.get(value)?.jdbcExample ?? `jdbc:${value}://host:port/database`
  );
}
