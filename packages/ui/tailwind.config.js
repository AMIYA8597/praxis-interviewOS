module.exports = {
  theme: {
    colors: require('./src/theme').colors,
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        }
      }
    }
  }
}
