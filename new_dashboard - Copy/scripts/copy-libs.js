const fs = require('fs');
const path = require('path');

// Paths
const nodeModules = path.join(__dirname, '..', 'node_modules');
const staticJs = path.join(__dirname, '..', 'static', 'js');

// Libraries to copy
const libraries = [
    {
        from: path.join(nodeModules, 'chart.js', 'dist', 'chart.js'),  // Changed from chart.umd.min.js
        to: path.join(staticJs, 'chart.min.js')
    },
    {
        from: path.join(nodeModules, 'moment', 'min', 'moment.min.js'),
        to: path.join(staticJs, 'moment.min.js')
    },
    {
        from: path.join(nodeModules, 'socket.io-client', 'dist', 'socket.io.min.js'),
        to: path.join(staticJs, 'socket.io.min.js')
    }
];

// Ensure static/js directory exists
if (!fs.existsSync(staticJs)) {
    fs.mkdirSync(staticJs, { recursive: true });
}

// Copy each library
libraries.forEach(lib => {
    try {
        // Check if source file exists
        if (!fs.existsSync(lib.from)) {
            // Try alternate paths for Chart.js
            if (lib.to.includes('chart.min.js')) {
                const alternativePaths = [
                    path.join(nodeModules, 'chart.js', 'dist', 'chart.umd.js'),
                    path.join(nodeModules, 'chart.js', 'dist', 'chart.min.js'),
                    path.join(nodeModules, 'chart.js', 'dist', 'chart.esm.js')
                ];
                
                for (const altPath of alternativePaths) {
                    if (fs.existsSync(altPath)) {
                        lib.from = altPath;
                        break;
                    }
                }
            }
        }

        fs.copyFileSync(lib.from, lib.to);
        console.log(`Copied ${path.basename(lib.from)} to ${path.basename(lib.to)}`);
    } catch (error) {
        console.error(`Error copying ${path.basename(lib.from)}:`, error.message);
    }
});