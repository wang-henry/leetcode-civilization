import random
from gql import Client
from gql import gql
from gql.transport.aiohttp import AIOHTTPTransport

transport = AIOHTTPTransport(url="https://leetcode.com/graphql/")
client = Client(transport=transport)


async def get_profile_summary(handle: str):
    query = gql(
        """query userPublicProfile($username: String!) {
  matchedUser(username: $username) {
    profile {
      aboutMe
    }
  }
}"""
    )
    result = await client.execute_async(query, {"username": handle})
    return result.get("matchedUser", {}).get("profile", {}).get("aboutMe")


async def get_solve_count(handle: str):
    query = gql(
        """query userProfileUserQuestionProgressV2($userSlug: String!) {
  userProfileUserQuestionProgressV2(userSlug: $userSlug) {
    numAcceptedQuestions {
      count
      difficulty
    }
  }
}"""
    )
    result = await client.execute_async(query, {"userSlug": handle})

    return {
        entry["difficulty"]: entry["count"]
        for entry in result["userProfileUserQuestionProgressV2"]["numAcceptedQuestions"]
    }


async def get_daily_question():
    query = gql(
        """
    query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      acRate
      difficulty
      titleSlug
    }
  }
}
    """
    )
    result = await client.execute_async(query)
    return result.get("activeDailyCodingChallengeQuestion")


async def get_recent_ac(handle: str):
    query = gql(
        """
    query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
    """
    )

    result = await client.execute_async(query, {"username": handle, "limit": 15})
    return result.get("recentAcSubmissionList", {})


async def get_random_problem(difficulty: str = "MEDIUM", retry: int = 0):
    
    if retry > 3:
        return None
    
    query = gql(
        """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      acRate
      difficulty
      title
      titleSlug
      paidOnly: isPaidOnly
    }
  }
}
    """
    )
    result = await client.execute_async(
        query,
        {
            "categorySlug": "all-code-essentials",
            "skip": 0,
            "limit": 1,
            "filters": {"difficulty": difficulty, "premiumOnly": False},
        },
    )
    total_problems = result["problemsetQuestionList"]["total"]
    result = await client.execute_async(
        query,
        {
            "categorySlug": "all-code-essentials",
            "skip": random.randint(0, max(0, total_problems - 100)),
            "limit": 100,
            "filters": {"difficulty": difficulty, "premiumOnly": False},
        },
    )
    questions = result["problemsetQuestionList"]["questions"]
    free_questions = list(filter(lambda q: not q["paidOnly"], questions))

    if not free_questions:
        # retry up to 3 times
        return await get_random_problem(difficulty=difficulty, retry=retry + 1)

    return random.choice(free_questions)
