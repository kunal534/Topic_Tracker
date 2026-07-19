const ModuleScopePlugin = require('react-dev-utils/ModuleScopePlugin');

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Remove the ModuleScopePlugin that blocks react-refresh/runtime.js
      // from being resolved when node_modules lives in a subdirectory.
      webpackConfig.resolve.plugins = webpackConfig.resolve.plugins.filter(
        (plugin) => !(plugin instanceof ModuleScopePlugin)
      );
      return webpackConfig;
    },
  },
};
