package com.maskql.acl;

import com.maskql.acl.policy.HardcodedPolicyStore;

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

public class MaskqlSystemAccessControl implements SystemAccessControl {

    private final HardcodedPolicyStore policy = new HardcodedPolicyStore();

    @Override
    public Set<String> filterCatalogs(SystemSecurityContext context, Set<String> catalogs) {
        String user = context.getIdentity().getUser();
        return policy.filterCatalogs(user, catalogs);
    }

    @Override
    public Set<String> filterSchemas(SystemSecurityContext context, String catalogName, Set<String> schemaNames) {
        String user = context.getIdentity().getUser();
        if (policy.isAdmin(user)) return schemaNames;
        if (policy.hasRole(user, "ANALYST") && "test_db".equalsIgnoreCase(catalogName)) return schemaNames;
        return Set.of();
    }

    @Override
    public Set<SchemaTableName> filterTables(SystemSecurityContext context, String catalogName, Set<SchemaTableName> tableNames) {
        String user = context.getIdentity().getUser();
        if (policy.isAdmin(user)) return tableNames;
        Set<SchemaTableName> out = new HashSet<>();
        for (SchemaTableName t : tableNames) {
            if (policy.canSelectTable(user, catalogName, t.getSchemaName(), t.getTableName())) out.add(t);
        }
        return out;
    }

    @Override
    public void checkCanSelectFromColumns(SystemSecurityContext context, CatalogSchemaTableName table, Set<String> columns) {
        String user = context.getIdentity().getUser();
        boolean ok = policy.canSelectTable(user,
                table.getCatalogName(),
                table.getSchemaTableName().getSchemaName(),
                table.getSchemaTableName().getTableName());
        if (!ok) {
            throw new AccessDeniedException("Access Denied: Cannot select from table " + table);
        }
    }

    @Override
    public List<ViewExpression> getRowFilters(SystemSecurityContext context, CatalogSchemaTableName table) {
        String user = context.getIdentity().getUser();
        Optional<String> filter = policy.rowFilterSql(
                user,
                table.getCatalogName(),
                table.getSchemaTableName().getSchemaName(),
                table.getSchemaTableName().getTableName()
        );
        if (filter.isEmpty()) return List.of();
        return List.of(ViewExpression.builder().expression(filter.get()).build());
    }

    
    @Override
    public Map<ColumnSchema, ViewExpression> getColumnMasks(SystemSecurityContext context,
                                                            CatalogSchemaTableName table,
                                                            List<ColumnSchema> columns) {
        String user = context.getIdentity().getUser();
        String catalog = table.getCatalogName();
        String schema  = table.getSchemaTableName().getSchemaName();
        String tbl     = table.getSchemaTableName().getTableName();

        Map<ColumnSchema, ViewExpression> out = new LinkedHashMap<>();
        for (ColumnSchema col : columns) {
            policy.columnMaskSql(user, catalog, schema, tbl, col.getName())
                .ifPresent(sql -> out.put(col, ViewExpression.builder().expression(sql).build()));
        }
        return out;
    }

    @Override
    public void checkCanExecuteQuery(Identity identity, QueryId queryId) {
        return; // All User can execute query
    }

    @Override
    public boolean canAccessCatalog(SystemSecurityContext context, String catalogName) {
        String user = context.getIdentity().getUser();
        if (policy.isAdmin(user)) return true;
        if (policy.hasRole(user, "ANALYST") && "test_db".equalsIgnoreCase(catalogName)) return true;
        return false;
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
