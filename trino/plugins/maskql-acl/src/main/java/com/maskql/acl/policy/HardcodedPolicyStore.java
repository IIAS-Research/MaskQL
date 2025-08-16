package com.maskql.acl.policy;

import java.util.*;

public final class HardcodedPolicyStore {

    // Basic roles
    private static final Map<String, Set<String>> USER_ROLES = Map.of(
            "admin",   Set.of("ADMIN"),
            "test", Set.of("ANALYST")
    );

    // Static MASK for testing
    private static final String NAME_MASK = "CASE WHEN name IS NULL THEN NULL WHEN length(name) <= 2 THEN name ELSE rpad(substring(name, 1, 2), length(name), '*') END";

    public Set<String> rolesForUser(String user) {
        return USER_ROLES.getOrDefault(user, Set.of());
    }

    public boolean isAdmin(String user) {
        return rolesForUser(user).contains("ADMIN");
    }

    public boolean hasRole(String user, String role) {
        return rolesForUser(user).contains(role);
    }

    public Set<String> filterCatalogs(String user, Set<String> input) {
        if (isAdmin(user)) return input; // Admin see everything
        if (hasRole(user, "ANALYST")) { // Analyst can see test_db
            return Set.of("test_db");
        }
        return Set.of();
    }

    public boolean canSelectTable(String user, String catalog, String schema, String table) {
        if (isAdmin(user)) return true;
        if (hasRole(user, "ANALYST")) {
            return "test_db".equalsIgnoreCase(catalog);
        }
        return false;
    }

    public Optional<String> rowFilterSql(String user, String catalog, String schema, String table) {
        if (isAdmin(user)) return Optional.empty();
        if (hasRole(user, "ANALYST")
                && "test_db".equalsIgnoreCase(catalog)
                && "public".equalsIgnoreCase(schema)
                && "client".equalsIgnoreCase(table)) {
            return Optional.of("name NOT LIKE 'Bob%'"); // Analyst can't see bob
        }
        return Optional.of("false"); // Other see nothing
    }

    public Optional<String> columnMaskSql(String user, String catalog, String schema, String table, String column) {
        if (isAdmin(user)) return Optional.empty();
        if (hasRole(user, "ANALYST")
                && "test_db".equalsIgnoreCase(catalog)
                && "public".equalsIgnoreCase(schema)
                && "client".equalsIgnoreCase(table)
                && "name".equalsIgnoreCase(column)) {
            return Optional.of(NAME_MASK);
        }
        return Optional.empty();
    }
}
