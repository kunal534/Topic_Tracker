import { gql } from "@apollo/client/core";

export const SUBSCRIPTIONS = gql`
  query Subscriptions {
    subscriptions { id cadence active topic { id name baselineSummary baselineUpdatedAt } }
    notifications(limit: 8) { id read createdAt topicUpdate { id title summary confidence detectedAt sourceUrls } }
  }
`;

export const TOPIC_UPDATES = gql`
  query TopicUpdates($topicId: ID!) {
    topicUpdates(topicId: $topicId) { id title summary confidence detectedAt sourceUrls serviceNotice }
  }
`;

export const REGISTER = gql`
  mutation Register($email: String!, $password: String!) {
    register(email: $email, password: $password) { accessToken }
  }
`;

export const LOGIN = gql`
  mutation Login($email: String!, $password: String!) {
    login(email: $email, password: $password) { accessToken }
  }
`;

export const CREATE_TOPIC = gql`
  mutation CreateTopic($name: String!) { createTopic(name: $name) { id name } }
`;

export const SUBSCRIBE = gql`
  mutation Subscribe($topicId: ID!, $cadence: String!) {
    subscribeToTopic(topicId: $topicId, cadence: $cadence) { id }
  }
`;

export const UNSUBSCRIBE = gql`
  mutation Unsubscribe($subscriptionId: ID!) { unsubscribeFromTopic(subscriptionId: $subscriptionId) }
`;

export const MARK_READ = gql`
  mutation MarkRead($notificationId: ID!) { markNotificationRead(notificationId: $notificationId) }
`;
