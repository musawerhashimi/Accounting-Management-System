curl -X POST http://localhost:8000/api/vendors/purchases/ \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": 1,
    "currency": 1,
    "notes": "",
    "items": [
      {
        "id": 2,
        "quantity": 5,
        "unit_cost": 10,
        "product_data": {
          "name": "Pan",
          "category_id": 3,
          "base_unit_id": 1,
          "description": "A pan for cooking",
          "reorder_level": 10,
          "variants": [
            {
              "variant_name": "Pan",
              "is_default": true,
              "barcode": "00000007",
              "cost_price": 10,
              "cost_currency_id": 1,
              "selling_price": 12,
              "selling_currency_id": 1
            }
          ]
        }
      }
    ]
  }'
