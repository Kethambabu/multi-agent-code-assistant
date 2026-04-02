def get_sample_data():
    return {
        'products': [
            {'id': 1, 'name': 'Product 1', 'price': 29.99},
            {'id': 2, 'name': 'Product 2', 'price': 39.99},
            {'id': 3, 'name': 'Product 3', 'price': 49.99}
        ],
        'features': [
            'Responsive Design',
            'Modern UI',
            'Easy to Use'
        ]
    }

def format_currency(amount):
    return f'${amount:.2f}'