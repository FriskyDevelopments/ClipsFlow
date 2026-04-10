Please review my changes to `services/media_processor.py`. I changed `_cleanup_intermediate_files` to use `asyncio.gather` instead of a sequential loop. Tests pass.
