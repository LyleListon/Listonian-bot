const fs = require('fs');
const path = require('path');
const https = require('https');

// Define static directories
const staticDir = path.join(__dirname, '..', 'static');
const cssDir = path.join(staticDir, 'css');
const jsDir = path.join(staticDir, 'js');
const imgDir = path.join(staticDir, 'img');

// Create directories
[staticDir, cssDir, jsDir, imgDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        console.log(`Created directory: ${dir}`);
    }
});

// Download CDN files
const files = [
    {
        url: 'https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.min.js',
        dest: path.join(jsDir, 'chart.min.js')
    },
    {
        url: 'https://cdn.jsdelivr.net/npm/moment@2.29.4/min/moment.min.js',
        dest: path.join(jsDir, 'moment.min.js')
    },
    {
        url: 'https://cdn.jsdelivr.net/npm/socket.io-client@4.6.0/dist/socket.io.min.js',
        dest: path.join(jsDir, 'socket.io.min.js')
    }
];

// Download function
function downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(dest);
        https.get(url, response => {
            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log(`Downloaded: ${dest}`);
                resolve();
            });
        }).on('error', err => {
            fs.unlink(dest, () => {});
            reject(err);
        });
    });
}

// Download all files
Promise.all(files.map(file => downloadFile(file.url, file.dest)))
    .then(() => {
        console.log('All files downloaded successfully');
    })
    .catch(err => {
        console.error('Error downloading files:', err);
    });