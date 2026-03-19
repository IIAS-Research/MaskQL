package com.maskql.acl;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

public class AclAPI {
    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8).replace("+", "%20");
    }

    private final URI baseUri;
    private final HttpClient client;
    private final ObjectMapper mapper;

    public AclAPI() { this("http://maskql:8081"); }
    public AclAPI(String baseUrl) {
        this.baseUri = URI.create(Objects.requireNonNull(baseUrl));
        this.client = HttpClient.newHttpClient();
        this.mapper = new ObjectMapper().setSerializationInclusion(JsonInclude.Include.NON_NULL);
    }

    // ---- helpers
    private URI buildUri(String path, String schema) {
        String url = baseUri.toString().replaceAll("/+$", "") + path;
        if (schema != null && !schema.isEmpty()) {
            url += "?schema=" + URLEncoder.encode(schema, StandardCharsets.UTF_8);
        }
        return URI.create(url);
    }
    private HttpResponse<String> postJson(URI uri, Object body) throws Exception {
        String json = mapper.writeValueAsString(body);
        HttpRequest req = HttpRequest.newBuilder(uri)
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }
    private HttpResponse<String> postNoBody(URI uri) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(uri)
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }
    private static void ensure2xx(HttpResponse<?> r) {
        int s = r.statusCode();
        if (s < 200 || s >= 300) throw new RuntimeException("HTTP " + s + " calling " + r.uri() + " body=" + r.body());
    }

    // ---- DTOs (pour le body)
    static class CatalogsIn { public List<String> catalogs; CatalogsIn(Collection<String> v){ this.catalogs = new ArrayList<>(v);} }
    static class SchemasIn  { public List<String> schemas;  SchemasIn(Collection<String> v){ this.schemas  = new ArrayList<>(v);} }
    static class TablesIn   { public List<String> tables;   TablesIn(Collection<String> v){ this.tables   = new ArrayList<>(v);} }
    static class ColumnsIn  { public List<String> columns;  ColumnsIn(Collection<String> v){ this.columns  = new ArrayList<>(v);} }

    // =======================
    // 1) POST /acl/{user}/catalog
    // =======================
    public List<String> catalogs(String user, Collection<String> catalogs) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/catalog", null);
        HttpResponse<String> resp = postJson(uri, new CatalogsIn(catalogs));
        ensure2xx(resp);
        return Arrays.asList(mapper.readValue(resp.body(), String[].class));
    }

    // =======================
    // 2) POST /acl/{user}/{catalog}/schemas
    // =======================
    public List<String> schemas(String user, String catalog, Collection<String> schemas) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/schemas", null);
        HttpResponse<String> resp = postJson(uri, new SchemasIn(schemas));
        ensure2xx(resp);
        return Arrays.asList(mapper.readValue(resp.body(), String[].class));
    }

    // =======================
    // 3) POST /acl/{user}/{catalog}/tables?schema=...
    // =======================
    public List<String> tables(String user, String catalog, String schema, Collection<String> tables) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/tables", schema);
        HttpResponse<String> resp = postJson(uri, new TablesIn(tables));
        ensure2xx(resp);
        return Arrays.asList(mapper.readValue(resp.body(), String[].class));
    }

    public List<String> columns(String user, String catalog, String table, String schema, Collection<String> columns) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/" + enc(table) + "/columns", schema);
        HttpResponse<String> resp = postJson(uri, new ColumnsIn(columns));
        ensure2xx(resp);
        return Arrays.asList(mapper.readValue(resp.body(), String[].class));
    }

    // =======================
    // 4) POST /acl/{user}/{catalog}/{table}/is_columns_allowed?schema=...
    // =======================
    public boolean isColumnsAllowed(String user, String catalog, String table, String schema, Collection<String> columns) throws Exception {
        List<String> allowed_columns = columns(user, catalog, table, schema, columns);
        boolean all_allowed = new java.util.HashSet<>(columns).equals(new java.util.HashSet<>(allowed_columns));

        return all_allowed;
    }

    // =======================
    // 5) POST /acl/{user}/{catalog}/{table}/row_filters?schema=...
    // =======================
    public String rowFilter(String user, String catalog, String table, String schema) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/" + enc(table) + "/row_filter", schema);
        HttpResponse<String> resp = postNoBody(uri);
        ensure2xx(resp);

        String body = resp.body();
        if (body == null || body.isBlank()) {
            return null;
        }

        var node = mapper.readTree(body);
        if (node == null || node.isNull() || !node.has("filter") || node.get("filter").isNull()) {
            return null;
        }

        String expr = node.get("filter").asText();
        expr = (expr == null) ? null : expr.trim();
        return (expr == null || expr.isEmpty()) ? null : expr;
    }



    // =======================
    // 6) POST /acl/{user}/{catalog}/{table}/{column}/mask?schema=...
    // =======================
    public Optional<String> mask(String user, String catalog, String table, String column, String schema) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/" + enc(table) + "/" + enc(column) + "/mask", schema);
        HttpResponse<String> resp = postNoBody(uri);
        ensure2xx(resp);

        String expr = mapper.readTree(resp.body()).path("mask").asText(); // "" if no mask
        expr = (expr == null) ? null : expr.trim();
        return (expr == null || expr.isEmpty()) ? Optional.empty() : Optional.of(expr);
    }

    public boolean canAccessCatalog(String user, String catalog) throws Exception {
        URI uri = buildUri("/acl/" + enc(user) + "/" + enc(catalog) + "/can_access", null);
        HttpResponse<String> resp = postNoBody(uri);
        ensure2xx(resp);
        Map<?, ?> m = mapper.readValue(resp.body(), Map.class);
        Object v = m.get("allowed");
        return (v instanceof Boolean) ? (Boolean) v : Boolean.parseBoolean(String.valueOf(v));
    }

}
