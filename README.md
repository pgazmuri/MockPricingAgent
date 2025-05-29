# Mock Drug Pricing Agent

A comprehensive demonstration of the OpenAI Assistant API with advanced function calling, showcasing realistic Pharmacy Benefits Manager (PBM) drug pricing workflows.

## Overview

This application demonstrates how to use the OpenAI Assistant API to create a sophisticated conversational agent that orchestrates multiple services to calculate accurate drug pricing, just like a real PBM system. 

**Key Innovation**: Instead of a single "pricing service", the system demonstrates realistic complexity by gathering data from multiple sources and performing mathematical calculations, showcasing how AI can coordinate complex business processes.

## Architecture: Real PBM Complexity

### Multiple Data Sources
The system demonstrates how real PBM pricing requires data from multiple services:

1. **🔍 NDC Lookup Service** - Find and disambiguate drugs
2. **✅ Eligibility Service** - Verify member coverage  
3. **📊 Plan Benefits Service** - Get detailed benefit structure and tier information
4. **📈 Utilization Service** - Member's year-to-date spending and deductible progress
5. **💊 Formulary Service** - Check drug coverage and tier placement
6. **💰 Drug Cost Service** - Wholesale and plan negotiated pricing
7. **🎫 Coupon Service** - Available manufacturer discounts and patient assistance
8. **🧮 Pricing Calculator** - Mathematical engine for accurate calculations

### Intelligent Orchestration
The OpenAI Assistant automatically:
- Determines which services to call based on user requests
- Sequences calls in the right order
- Gathers all required data before calculating final pricing
- Uses a mathematical calculator to ensure accuracy
- Explains the calculation process step-by-step

## Key Features Demonstrated

### Advanced Function Calling
- **Sequential Dependencies**: Some functions require data from previous calls
- **Complex Workflows**: Multi-step processes with decision points
- **Data Aggregation**: Combining data from multiple sources
- **Mathematical Accuracy**: Dedicated calculator for pricing logic

### Realistic PBM Business Logic
- **Deductible Calculations**: How much member has met vs. remaining
- **Tier-based Benefits**: Different copays/coinsurance by drug tier
- **Out-of-Pocket Protection**: Annual maximum calculations
- **Coupon Stacking**: Multiple discount programs applied correctly
- **Formulary Restrictions**: Prior auth, step therapy, quantity limits

### Natural Language Interface
- **Intent Recognition**: Understanding pricing requests in natural language
- **Disambiguation**: Helping users find the right drug from multiple options
- **Explanation**: Clear breakdown of how costs are calculated
- **Error Handling**: Graceful handling of missing data or API errors

## Project Structure

```
MockPricingAgent/
├── main.py                 # Main CLI application with rich UI
├── assistant_manager.py    # OpenAI Assistant API management
├── mock_services.py        # Mock PBM services using OpenAI API
├── models.py              # Pydantic data models
├── keys.py                # API keys (gitignored)
├── requirements.txt       # Python dependencies
├── .gitignore            # Ignore sensitive files
└── README.md             # This file
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   Edit `keys.py` and add your OpenAI API key:
   ```python
   OPENAI_API_KEY = "your-actual-openai-api-key-here"
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## Usage Examples

### Basic Drug Search
```
You: I need pricing for metformin
🔧 Calling function: ndc_lookup with args: {'search_term': 'metformin'}
Assistant: I found several metformin options. Here are the available choices:
1. Metformin 500mg tablets (Generic) - NDC: 12345-678-90
2. Metformin 1000mg tablets (Generic) - NDC: 23456-789-01
...
Which strength and form do you need?
```

### Complete Pricing Workflow
```
You: What will my Lipitor 20mg cost? My member ID is ABC123456
🔧 Calling function: ndc_lookup with args: {'search_term': 'Lipitor 20mg'}
🔧 Calling function: check_eligibility with args: {'member_id': 'ABC123456'}
🔧 Calling function: calculate_pricing with args: {'ndc': '12345-678-90', 'member_id': 'ABC123456'}
Assistant: Based on your plan benefits, here's your Lipitor pricing:
- Plan copay: $25.00
- Available manufacturer coupon: $10.00 savings
- Your final cost: $15.00
...
```

## Architecture

### Function Calling Flow
1. User asks about drug pricing in natural language
2. Assistant analyzes the request and determines which functions to call
3. Functions are executed against mock services (powered by OpenAI)
4. Results are returned to the assistant
5. Assistant provides a natural language response with the information

### Mock Services Design
- Each "service" uses OpenAI's Completions API to generate realistic data
- Services return structured data using Pydantic models
- Responses are contextually appropriate and varied
- Demonstrates real-world PBM service complexity

## Key Learning Points

1. **Assistant API Benefits**: Shows how assistants can orchestrate complex workflows automatically
2. **Function Calling**: Demonstrates seamless integration between AI and external services
3. **Conversation Context**: Assistant maintains context across multiple function calls
4. **Error Handling**: Graceful handling of API errors and edge cases
5. **User Experience**: Natural language interface for complex business processes

## Customization

- **Add More Functions**: Extend with additional PBM services (prior auth, formulary checks, etc.)
- **Enhance Models**: Add more detailed drug and plan information
- **Improve UI**: Add web interface or integrate with existing systems
- **Real Services**: Replace mock services with actual PBM API calls

## Dependencies

- `openai>=1.12.0` - OpenAI Python SDK
- `pydantic>=2.5.0` - Data validation and modeling
- `rich>=13.7.0` - Rich terminal UI
- `python-dotenv>=1.0.0` - Environment variable management

## License

This is a demonstration project for educational purposes.
