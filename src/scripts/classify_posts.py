import asyncio
from loguru import logger
from sqlalchemy import select
from src.analyzer import LeadAnalyzer
from src.database import init_db, SessionLocal, Post, check_duplicate_lead
from dotenv import load_dotenv

async def main():
    load_dotenv()
    await init_db()
    logger.info("Starting post classification...")

    try:
        async with SessionLocal() as db:
            analyzer = LeadAnalyzer(batch_size=10)
            
            unclassified_posts_query = select(Post).filter(Post.is_lead == None)
            unclassified_posts_result = await db.execute(unclassified_posts_query)
            unclassified_posts = unclassified_posts_result.scalars().all()

            if not unclassified_posts:
                logger.info("No unclassified posts found. Exiting.")
                return

            logger.info(f"Found {len(unclassified_posts)} unclassified posts.")

            post_data_for_analysis = [
                {"id": p.post_id, "content": p.content, "author": p.author, "user_id": p.user_id}
                for p in unclassified_posts
            ]
            
            all_analyzed_posts_data = []
            for i, batch in enumerate(analyzer.batch_posts(post_data_for_analysis), 1):
                logger.info(f"Analyzing batch {i} ({len(batch)} posts)...")
                analyzed_batch = await analyzer.analyze_posts_batch(batch)
                all_analyzed_posts_data.extend(analyzed_batch)

            for analyzed_post_data in all_analyzed_posts_data:
                post_id = analyzed_post_data["id"]
                is_lead = analyzed_post_data["is_lead"]
                
                if is_lead:
                    post_query = select(Post).filter(Post.post_id == post_id)
                    post_result = await db.execute(post_query)
                    current_post = post_result.scalar_one_or_none()
                    
                    if current_post:
                        is_duplicate = await check_duplicate_lead(
                            db, 
                            current_post.user_id, 
                            current_post.content,
                            similarity_threshold=80.0
                        )
                        
                        if is_duplicate:
                            logger.info(f"Skipping duplicate lead for post {post_id} from user {current_post.author}")
                            is_lead = False
                        else:
                            logger.info(f"Added new lead for post {post_id} from user {current_post.author}")

                post_to_update_query = select(Post).filter(Post.post_id == post_id)
                post_to_update_result = await db.execute(post_to_update_query)
                post_to_update = post_to_update_result.scalar_one_or_none()

                if post_to_update:
                    post_to_update.is_lead = is_lead
                    db.add(post_to_update)
            
            await db.commit()
            logger.success("Post classification completed successfully!")

    except Exception as e:
        logger.exception(f"Fatal error during post classification: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
