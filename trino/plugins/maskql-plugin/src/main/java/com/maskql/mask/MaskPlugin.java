package com.maskql.mask;

import com.maskql.nlp.EdsPseudoBridge;
import io.trino.spi.Plugin;
import java.util.Set;

public class MaskPlugin implements Plugin {
  @Override
  public Set<Class<?>> getFunctions() {
    EdsPseudoBridge.getInstance().initialize();
    return Set.of(MaskUnstructured.class, MaskStructured.class);
  }
}
