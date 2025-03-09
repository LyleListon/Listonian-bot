/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/**/*.js",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Custom colors for our theme
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                },
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            fontSize: {
                'xxs': '0.625rem',
            },
            spacing: {
                '72': '18rem',
                '84': '21rem',
                '96': '24rem',
            },
            maxHeight: {
                '0': '0',
                '1/4': '25%',
                '1/2': '50%',
                '3/4': '75%',
                'full': '100%',
            },
            minWidth: {
                '0': '0',
                '1/4': '25%',
                '1/2': '50%',
                '3/4': '75%',
                'full': '100%',
            },
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
    ],
    variants: {
        extend: {
            opacity: ['disabled'],
            cursor: ['disabled'],
            backgroundColor: ['active', 'disabled'],
            textColor: ['active', 'disabled'],
            borderColor: ['active', 'disabled'],
        },
    },
}