package com.maskql.acl;

import io.trino.spi.security.SystemAccessControl;
import io.trino.spi.security.SystemAccessControlFactory;

import java.util.Map;


public class MaskqlSystemAccessControlFactory implements SystemAccessControlFactory {

    public static final String NAME = "maskql-acl";

    @Override
    public String getName() {
        return NAME;
    }

    public SystemAccessControl create(Map<String, String> config,
            SystemAccessControlFactory.SystemAccessControlContext context) {
        return new MaskqlSystemAccessControl();
    }
}
