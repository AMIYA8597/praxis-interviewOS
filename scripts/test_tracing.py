import asyncio
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.propagate import inject, extract
from fastapi import Request

# Setup simple console export for test
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

async def simulate_core_api_upload():
    with tracer.start_as_current_span("POST /api/resumes") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/api/resumes")
        
        # Simulate inserting DB row
        with tracer.start_as_current_span("db_insert_resume"):
            await asyncio.sleep(0.01)
            
        # Enqueue Job
        trace_carrier = {}
        inject(trace_carrier)
        print(f"[Core API] Injected Carrier: {trace_carrier}")
        
        return trace_carrier

async def simulate_worker_process(trace_carrier):
    # Worker extracts context
    otel_ctx = extract(trace_carrier)
    
    with tracer.start_as_current_span("process_resume", context=otel_ctx) as span:
        span.set_attribute("document_id", "doc-123")
        
        # Simulate worker steps
        with tracer.start_as_current_span("pdf_parsing"):
            await asyncio.sleep(0.01)
            
        with tracer.start_as_current_span("router_attempt"):
            await asyncio.sleep(0.02)

async def main():
    print("Starting cross-process trace simulation...")
    carrier = await simulate_core_api_upload()
    
    print("\nStarting worker process simulation...")
    await simulate_worker_process(carrier)

if __name__ == "__main__":
    asyncio.run(main())
