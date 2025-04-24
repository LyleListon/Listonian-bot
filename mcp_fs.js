#!/usr/bin/env node
/**
 * MCP Filesystem Client - Node.js version
 * 
 * A simple client for communicating with the filesystem MCP server using Node.js.
 */

const { spawn } = require('child_process');
const readline = require('readline');

// Function to send a request to the MCP server and get the response
async function sendRequest(toolName, args) {
  return new Promise((resolve, reject) => {
    // Start the MCP server process
    const process = spawn('npx', ['-y', '@modelcontextprotocol/server-filesystem', '/home/lylepaul78'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Create readline interface for reading responses
    const rl = readline.createInterface({
      input: process.stdout,
      crlfDelay: Infinity
    });

    // Handle errors
    process.stderr.on('data', (data) => {
      console.error(`MCP server error: ${data}`);
    });

    // Handle response
    rl.once('line', (line) => {
      try {
        const response = JSON.parse(line);
        resolve(response);
      } catch (error) {
        reject(new Error(`Failed to parse response: ${error.message}`));
      } finally {
        // Clean up
        process.kill();
        rl.close();
      }
    });

    // Send the request
    const request = {
      type: 'tool_call',
      request_id: 'req1',
      tool_name: toolName,
      arguments: args
    };

    process.stdin.write(JSON.stringify(request) + '\n');
  });
}

// Parse command line arguments
const [,, command, ...args] = process.argv;

// Show usage if no command provided
if (!command) {
  console.log('Usage: node mcp_fs.js <command> [arguments]');
  console.log('');
  console.log('Available commands:');
  console.log('  read <path>                  - Read a file');
  console.log('  write <path> <content>       - Write to a file');
  console.log('  list <path>                  - List directory contents');
  console.log('  mkdir <path>                 - Create a directory');
  console.log('  search <path> <pattern>      - Search for files');
  console.log('  info <path>                  - Get file info');
  console.log('');
  console.log('Examples:');
  console.log('  node mcp_fs.js read /path/to/file.txt');
  console.log('  node mcp_fs.js write /path/to/file.txt "Hello, world!"');
  console.log('  node mcp_fs.js list /path/to/directory');
  process.exit(1);
}

// Execute the command
async function main() {
  try {
    let response;
    
    switch (command) {
      case 'read':
        if (args.length !== 1) {
          console.error('Usage: node mcp_fs.js read <path>');
          process.exit(1);
        }
        response = await sendRequest('read_file', { path: args[0] });
        break;
        
      case 'write':
        if (args.length !== 2) {
          console.error('Usage: node mcp_fs.js write <path> <content>');
          process.exit(1);
        }
        response = await sendRequest('write_file', { path: args[0], content: args[1] });
        break;
        
      case 'list':
        if (args.length !== 1) {
          console.error('Usage: node mcp_fs.js list <path>');
          process.exit(1);
        }
        response = await sendRequest('list_directory', { path: args[0] });
        break;
        
      case 'mkdir':
        if (args.length !== 1) {
          console.error('Usage: node mcp_fs.js mkdir <path>');
          process.exit(1);
        }
        response = await sendRequest('create_directory', { path: args[0] });
        break;
        
      case 'search':
        if (args.length !== 2) {
          console.error('Usage: node mcp_fs.js search <path> <pattern>');
          process.exit(1);
        }
        response = await sendRequest('search_files', { path: args[0], pattern: args[1] });
        break;
        
      case 'info':
        if (args.length !== 1) {
          console.error('Usage: node mcp_fs.js info <path>');
          process.exit(1);
        }
        response = await sendRequest('get_file_info', { path: args[0] });
        break;
        
      default:
        console.error(`Unknown command: ${command}`);
        console.error('Run node mcp_fs.js without arguments to see usage');
        process.exit(1);
    }
    
    // Print the response
    if (response.type === 'response') {
      console.log(JSON.stringify(response.content, null, 2));
    } else {
      console.error('Error:', response);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main();