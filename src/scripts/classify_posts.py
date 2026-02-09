import asyncio
import argparse
from loguru import logger
from sqlalchemy import select
from src.analyzer import LeadAnalyzer
from src.database import init_db, SessionLocal, Post, check_duplicate_lead
from src.bot_config import get_bot_config, get_all_bot_configs
from dotenv import load_dotenv

async def classify_bot(bot_id: str):
    """Classify posts for a specific bot."""
    bot_config = get_bot_config(bot_id)
    logger.info(f"Starting classification for bot: {bot_config.name} ({bot_id})")
    
    await init_db(bot_id=bot_id, group_ids=bot_config.groups)

    try:
        async with SessionLocal() as db:
            analyzer = LeadAnalyzer(
                batch_size=10,
                system_prompt=bot_config.classification_prompt
            )
            
            unclassified_posts_query = select(Post).filter(
                Post.is_lead == None,
                Post.bot_id == bot_id
            )
            unclassified_posts_result = await db.execute(unclassified_posts_query)
            unclassified_posts = unclassified_posts_result.scalars().all()

            if not unclassified_posts:
                logger.info(f"No unclassified posts found for bot {bot_id}. Exiting.")
                return

            logger.info(f"Found {len(unclassified_posts)} unclassified posts for bot {bot_id}.")

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
                            bot_id=bot_id,
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
            logger.success(f"Post classification completed successfully for bot {bot_id}!")

    except Exception as e:
        logger.exception(f"Fatal error during post classification for bot {bot_id}: {e}")
        raise

async def main():
    load_dotenv()
    logger.info("Starting post classification...")
    
    parser = argparse.ArgumentParser(description="Classify posts as leads")
    parser.add_argument(
        "--bot",
        type=str,
        default="leasing",
        help="Bot ID to run classification for (default: leasing). Use 'all' to run for all enabled bots."
    )
    args = parser.parse_args()
    
    if args.bot == "all":
        bots = get_all_bot_configs(enabled_only=True)
        logger.info(f"Running classification for {len(bots)} enabled bots")
        
        for bot_config in bots:
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting bot: {bot_config.name} ({bot_config.bot_id})")
            logger.info(f"{'='*80}\n")
            await classify_bot(bot_config.bot_id)
    else:
        await classify_bot(args.bot)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
