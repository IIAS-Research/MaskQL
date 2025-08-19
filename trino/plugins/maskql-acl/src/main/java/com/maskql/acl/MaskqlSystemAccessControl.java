package com.maskql.acl;

import com.maskql.acl.AclAPI;

import io.trino.spi.connector.CatalogSchemaTableName;
import io.trino.spi.connector.ColumnSchema;
import io.trino.spi.connector.SchemaTableName;

import io.trino.spi.security.AccessDeniedException;
import io.trino.spi.security.Identity;
import io.trino.spi.security.SystemAccessControl;
import io.trino.spi.security.SystemSecurityContext;
import io.trino.spi.security.ViewExpression;
import io.trino.spi.QueryId;

import java.security.Principal;
import java.util.*;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;


public class MaskqlSystemAccessControl implements SystemAccessControl {

    private final AclAPI aclApi = new AclAPI();
    private static final String BASE_URL = "http://maskql:8081";
    private static final HttpClient CLIENT = HttpClient.newHttpClient();
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    public void checkCanCreateCatalog(SystemSecurityContext context, String catalog) {
        String user = context.getIdentity().getUser();
        
        if (!user.equals("maskql-admin")) {
            throw new AccessDeniedException("Access Denied: Cannot create catalog " + catalog);
        }
    }

    @Override
    public void checkCanDropCatalog(SystemSecurityContext context, String catalog) {
        String user = context.getIdentity().getUser();
        if (!user.equals("maskql-admin")) {
            throw new AccessDeniedException("Access Denied: Cannot drop catalog " + catalog);
        }
    }

    @Override
    public Set<String> filterCatalogs(SystemSecurityContext context, Set<String> catalogs) {
        String user = context.getIdentity().getUser();
        try {
            List<String> allowed = aclApi.catalogs(user, catalogs);
            return new HashSet<>(allowed);
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] filterCatalogs error: " + e.getClass().getName() + ": " + e.getMessage());
            // return catalogs; // DEBUG -> Allow all
            return Collections.emptySet();
        }
    }

    @Override
    public Set<String> filterSchemas(SystemSecurityContext context, String catalogName, Set<String> schemaNames) {
        String user = context.getIdentity().getUser();
        try {
            List<String> allowed = aclApi.schemas(user, catalogName, schemaNames);
            return new LinkedHashSet<>(allowed);
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] filterSchemas error: " + e.getClass().getName() + ": " + e.getMessage());
            return Collections.emptySet();
        }
    }

    @Override
    public Set<SchemaTableName> filterTables(SystemSecurityContext context, String catalogName, Set<SchemaTableName> tableNames) {
        String user = context.getIdentity().getUser();
        try {
            // Group requested tables by schema because the API takes one schema per call
            Map<String, List<String>> bySchema = new LinkedHashMap<>();
            for (SchemaTableName t : tableNames) {
                String schema = t.getSchemaName(); // can be null depending on connector; handle as key "null"
                bySchema.computeIfAbsent(schema, k -> new ArrayList<>()).add(t.getTableName());
            }

            Set<SchemaTableName> out = new LinkedHashSet<>();
            for (Map.Entry<String, List<String>> e : bySchema.entrySet()) {
                String schema = e.getKey();
                List<String> tables = e.getValue();
                List<String> allowed = aclApi.tables(user, catalogName, schema, tables);
                for (String tbl : allowed) {
                    out.add(new SchemaTableName(schema, tbl));
                }
            }
            return out;
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] filterTables error: " + e.getClass().getName() + ": " + e.getMessage());
            return Collections.emptySet();
        }
    }

    @Override
    public void checkCanSelectFromColumns(SystemSecurityContext context, CatalogSchemaTableName table, Set<String> columns) {
        String user    = context.getIdentity().getUser();
        String catalog = table.getCatalogName();
        String schema  = table.getSchemaTableName().getSchemaName(); // may be null
        String tbl     = table.getSchemaTableName().getTableName();

        try {
            boolean ok = aclApi.isColumnsAllowed(user, catalog, tbl, schema, columns);
            if (!ok) {
                throw new AccessDeniedException("Access Denied: Cannot select from table " + table);
            }
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] checkCanSelectFromColumns error: " + e.getClass().getName() + ": " + e.getMessage());
            throw new AccessDeniedException("Access Denied (policy API failure) for table " + table);
        }
    }

    @Override
    public List<ViewExpression> getRowFilters(SystemSecurityContext context, CatalogSchemaTableName table) {
        String user    = context.getIdentity().getUser();
        String catalog = table.getCatalogName();
        String schema  = table.getSchemaTableName().getSchemaName();
        String tbl     = table.getSchemaTableName().getTableName();

        try {
            // API returns a list (could be strings or objects). AclAPI.rowFilters() returns List<Map<String,Object>>
            List<Map<String, Object>> filters = aclApi.rowFilters(user, catalog, tbl, schema);
            if (filters == null || filters.isEmpty()) {
                return List.of();
            }
            List<ViewExpression> out = new ArrayList<>();
            for (Object item : filters) {
                // accept plain strings or maps with "expression"/"sql"
                String expr = null;
                if (item instanceof String) {
                    expr = (String) item;
                } else if (item instanceof Map) {
                    Object v = ((Map<?, ?>) item).get("expression");
                    if (v == null) v = ((Map<?, ?>) item).get("sql");
                    if (v != null) expr = String.valueOf(v);
                }
                if (expr != null && !expr.isBlank()) {
                    out.add(ViewExpression.builder().expression(expr).build());
                }
            }
            return out;
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] rowFilters error: " + e.getClass().getName() + ": " + e.getMessage());

            List<ViewExpression> out = new ArrayList<>();
            out.add(ViewExpression.builder().expression("false").build());
            return out;
        }
    }

    @Override
    public Map<ColumnSchema, ViewExpression> getColumnMasks(SystemSecurityContext context,
                                                            CatalogSchemaTableName table,
                                                            List<ColumnSchema> columns) {
        String user    = context.getIdentity().getUser();
        String catalog = table.getCatalogName();
        String schema  = table.getSchemaTableName().getSchemaName(); // can be null
        String tbl     = table.getSchemaTableName().getTableName();

        Map<ColumnSchema, ViewExpression> out = new LinkedHashMap<>();
        try {
            for (ColumnSchema col : columns) {
                String colName = col.getName();
                Optional<String> expr = aclApi.mask(user, catalog, tbl, colName, schema);
                expr.ifPresent(sql ->
                    out.put(col, ViewExpression.builder().expression(sql).build())
                );
            }
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] getColumnMasks error: " + e.getClass().getName() + ": " + e.getMessage());
            out.clear();
        }
        return out;
    }

    @Override
    public boolean canAccessCatalog(SystemSecurityContext context, String catalogName) {
        String user = context.getIdentity().getUser();
        try {
            return aclApi.canAccessCatalog(user, catalogName);
        } catch (Exception e) {
            System.err.println("[MaskQL ACL] canAccessCatalog error: " + e.getClass().getName() + ": " + e.getMessage());
            return false;
        }
    }

    // TODO Do we keep this ?
    @Override
    public void checkCanExecuteQuery(Identity identity, QueryId queryId) {
        return; // All User can execute query
    }

    // Some kind of disabled Trino access controls
    // TODO Check is this is still usefull
    @Override
    public void checkCanSetUser(Optional<Principal> principal, String userName) {
        return; // Always able to set user
    }

    @Override
    public void checkCanImpersonateUser(Identity identity, String targetUser) {
        return; // Always can impersonate, only MaskQL can talk to Trino
        // TODO Check if query parameter can cheat on this
    }

}
