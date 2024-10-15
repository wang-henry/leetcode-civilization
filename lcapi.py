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
