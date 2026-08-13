import type { ComponentType } from 'svelte';
import type { ComponentItem } from '$lib/api';

export interface PluginTab {
  id: string;
  label: string;
  icon?: ComponentType;
  component: ComponentType;
  isVisible?: (component: ComponentItem) => boolean;
}

export interface PluginDefinition {
  id: string;
  name: string;
  version?: string;
  description?: string;
  category?: 'auth' | 'scm' | 'cicd' | 'observability' | 'general';
  icon?: ComponentType;
  tabs?: PluginTab[];
  configComponent?: ComponentType;
}

class PluginRegistry {
  private plugins: Map<string, PluginDefinition> = new Map();

  register(plugin: PluginDefinition): void {
    this.plugins.set(plugin.id, plugin);
  }

  getPlugin(id: string): PluginDefinition | undefined {
    return this.plugins.get(id);
  }

  getAllPlugins(): PluginDefinition[] {
    return Array.from(this.plugins.values());
  }

  getConfigurablePlugins(): PluginDefinition[] {
    return this.getAllPlugins().filter((p) => Boolean(p.configComponent));
  }

  getTabsForComponent(component: ComponentItem): PluginTab[] {
    const tabs: PluginTab[] = [];
    for (const plugin of this.plugins.values()) {
      if (plugin.tabs) {
        for (const tab of plugin.tabs) {
          if (!tab.isVisible || tab.isVisible(component)) {
            tabs.push(tab);
          }
        }
      }
    }
    return tabs;
  }
}

export const pluginRegistry = new PluginRegistry();
