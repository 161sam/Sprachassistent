#!/usr/bin/env node
// Wrapper around Cordova CLI to ensure numeric exit codes
require('loud-rejection/register');
const util = require('util');
const { events, CordovaError } = require('cordova-common');
const cli = require('cordova/src/cli');

cli(process.argv).catch(err => {
  if (!(err instanceof Error)) {
    const errorOutput = typeof err === 'string' ? err : util.inspect(err);
    throw new CordovaError('Promise rejected with non-error: ' + errorOutput);
  }
  const code = typeof err.code === 'number' ? err.code : 1;
  process.exitCode = code;
  console.error(err.message);
  events.emit('verbose', err.stack);
});
