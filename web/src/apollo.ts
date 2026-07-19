import { ApolloClient, ApolloLink, HttpLink, InMemoryCache } from "@apollo/client/core";

const httpLink = new HttpLink({
  uri: process.env.REACT_APP_GRAPHQL_URL ?? "http://localhost:8000/graphql",
});

const appEnv = process.env.REACT_APP_ENV ?? "development";
const devUserId = process.env.REACT_APP_DEV_USER_ID ?? "development-user";

const authLink = new ApolloLink((operation, forward) => {
  const token = localStorage.getItem("topic-tracker-token");
  operation.setContext(({ headers = {} }) => ({
    headers: {
      ...headers,
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(appEnv === "development" ? { "x-user-id": devUserId } : {}),
    },
  }));
  return forward(operation);
});

export const client = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache({
    typePolicies: {
      Topic: { keyFields: ["id"] },
      Subscription: { keyFields: ["id"] },
      TopicUpdate: { keyFields: ["id"] },
      Notification: { keyFields: ["id"] },
      Query: {
        fields: {
          topicUpdates: {
            keyArgs: ["topicId"],
            merge: false,
          },
        },
      },
    },
  }),
});
