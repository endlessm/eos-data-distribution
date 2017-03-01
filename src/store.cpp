/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/**
 * Copyright (c) 2013-2016 Regents of the University of California.
 *
 * This file is part of ndn-cxx library (NDN C++ library with eXperimental eXtensions).
 *
 * ndn-cxx library is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Lesser General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later version.
 *
 * ndn-cxx library is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.
 *
 * You should have received copies of the GNU General Public License and GNU Lesser
 * General Public License along with ndn-cxx, e.g., in COPYING.md file.  If not, see
 * <http://www.gnu.org/licenses/>.
 *
 * See AUTHORS.md for complete list of ndn-cxx authors and contributors.
 *
 * @author Alexander Afanasyev <http://lasr.cs.ucla.edu/afanasyev/index.html>
 */

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/util/scheduler.hpp>
#include "chunks/consumer/consumer.hpp"

using namespace ndn;
namespace store {

class ConsumerWithTimer : noncopyable
{
public:
  ConsumerWithTimer()
    : m_face(m_ioService) // Create face with io_service object
    , m_scheduler(m_ioService)
    , m_name("/example/testApp/randomData")
  {
  }

  void
  run()
  {
    Interest interest(m_name);
    interest.setInterestLifetime(time::seconds(1));
    interest.setMustBeFresh(true);

    ValidatorNull validator;
    Consumer consumer(validator, options.isVerbose);

    BOOST_ASSERT(discover != nullptr);
    BOOST_ASSERT(pipeline != nullptr);
    consumer.run(std::move(discover), std::move(pipeline));

    ConsumerWithTimer::expressInterest(interest);

    std::cout << "Sending " << interest << std::endl;

    // Schedule a new event
    m_scheduler.scheduleEvent(time::seconds(2),
                              bind(&ConsumerWithTimer::delayedInterest, this));

    // m_ioService.run() will block until all events finished or m_ioService.stop() is called
    m_ioService.run();

    // Alternatively, m_face.processEvents() can also be called.
    // processEvents will block until the requested data received or timeout occurs.
    // m_face.processEvents();
  }

private:
  void
  expressInterest (const Interest& interest)
  {
    m_face.expressInterest(interest,
                           bind(&ConsumerWithTimer::onData, this, _1, _2),
                           bind(&ConsumerWithTimer::onNack, this, _1, _2),
                           bind(&ConsumerWithTimer::onTimeout, this, _1));
  }

  void
  onData(const Interest& interest, const Data& data)
  {
    std::cout << data << std::endl;
  }

  void
  onNack(const Interest& interest, const lp::Nack& nack)
  {
    std::cout << "received Nack with reason " << nack.getReason()
              << " for interest " << interest << std::endl;
  }

  void
  onTimeout(const Interest& interest)
  {
    std::cout << "Timeout " << interest << std::endl;
    std::cout << "Re-sending " << interest << std::endl;
    ConsumerWithTimer::expressInterest(interest);
  }

  void
  delayedInterest()
  {
    std::cout << "One more Interest, delayed by the scheduler" << std::endl;

    Interest interest(m_name);
    interest.setInterestLifetime(time::milliseconds(1000));
    interest.setMustBeFresh(true);

    ConsumerWithTimer::expressInterest(interest);

    std::cout << "Sending " << interest << std::endl;
  }

private:
  // Explicitly create io_service object, which can be shared between Face and Scheduler
  boost::asio::io_service m_ioService;
  Face m_face;
  Name m_name;
  Scheduler m_scheduler;
};
}

int
main(int argc, char** argv)
{
  store::ConsumerWithTimer consumer;
  try {
    consumer.run();
  }
  catch (const std::exception& e) {
    std::cerr << "ERROR: " << e.what() << std::endl;
  }
  return 0;
}
