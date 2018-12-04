/////////////////////////////////////////////////////////////////////////
///@author ��̩֤ȯ�ɷ����޹�˾
///@file xtp_quote_api.h
///@brief �������鶩�Ŀͻ��˽ӿ�
/////////////////////////////////////////////////////////////////////////

#ifndef _XTP_QUOTE_API_H_
#define _XTP_QUOTE_API_H_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "xtp_api_struct.h"

#if defined(ISLIB) && defined(WIN32)
#ifdef LIB_MD_API_EXPORT
#define MD_API_EXPORT __declspec(dllexport)
#else
#define MD_API_EXPORT __declspec(dllimport)
#endif
#else
#define MD_API_EXPORT 
#endif

/*!
* \class XTP::API::QuoteSpi
*
* \brief ����ص���
*
* \author ��̩֤ȯ�ɷ����޹�˾
* \date ʮ�� 2015
*/
namespace XTP {
	namespace API {
		class QuoteSpi
		{
		public:

			///���ͻ����������̨ͨ�����ӶϿ�ʱ���÷��������á�
			///@param reason ����ԭ��������������Ӧ
			///@remark api�����Զ������������߷���ʱ�����û�����ѡ����������������ڴ˺����е���Login���µ�¼��ע���û����µ�¼����Ҫ���¶�������
			virtual void OnDisconnected(int reason) {};


			///����Ӧ��
			///@param error_info ����������Ӧ��������ʱ�ľ���Ĵ������ʹ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@remark �˺���ֻ���ڷ�������������ʱ�Ż���ã�һ�������û�����
			virtual void OnError(XTPRI *error_info) {};

			///��������Ӧ��
			///@param ticker ��ϸ�ĺ�Լ�������
			///@param error_info ���ĺ�Լ��������ʱ�Ĵ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@param is_last �Ƿ�˴ζ��ĵ����һ��Ӧ�𣬵�Ϊ���һ����ʱ��Ϊtrue�����Ϊfalse����ʾ��������������Ϣ��Ӧ
			///@remark ÿ�����ĵĺ�Լ����Ӧһ������Ӧ����Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnSubMarketData(XTPST *ticker, XTPRI *error_info, bool is_last) {};

			///ȡ����������Ӧ��
			///@param ticker ��ϸ�ĺ�Լȡ���������
			///@param error_info ȡ�����ĺ�Լʱ��������ʱ���صĴ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@param is_last �Ƿ�˴�ȡ�����ĵ����һ��Ӧ�𣬵�Ϊ���һ����ʱ��Ϊtrue�����Ϊfalse����ʾ��������������Ϣ��Ӧ
			///@remark ÿ��ȡ�����ĵĺ�Լ����Ӧһ��ȡ������Ӧ����Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnUnSubMarketData(XTPST *ticker, XTPRI *error_info, bool is_last) {};

			///����֪ͨ
			///@param market_data �������ݣ���Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnMarketData(XTPMD *market_data) {};

			///�������鶩����Ӧ�𣨴˺����ӿ�Ϊ�����ӿڣ������ݲ�֧�֣�
			///@param ticker ��ϸ�ĺ�Լ�������
			///@param error_info ���ĺ�Լ��������ʱ�Ĵ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@param is_last �Ƿ�˴ζ��ĵ����һ��Ӧ�𣬵�Ϊ���һ����ʱ��Ϊtrue�����Ϊfalse����ʾ��������������Ϣ��Ӧ
			///@remark ÿ�����ĵĺ�Լ����Ӧһ������Ӧ����Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnSubOrderBook(XTPST *ticker, XTPRI *error_info, bool is_last) {};

			///ȡ���������鶩����Ӧ�𣨴˺����ӿ�Ϊ�����ӿڣ������ݲ�֧�֣�
			///@param ticker ��ϸ�ĺ�Լȡ���������
			///@param error_info ȡ�����ĺ�Լʱ��������ʱ���صĴ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@param is_last �Ƿ�˴�ȡ�����ĵ����һ��Ӧ�𣬵�Ϊ���һ����ʱ��Ϊtrue�����Ϊfalse����ʾ��������������Ϣ��Ӧ
			///@remark ÿ��ȡ�����ĵĺ�Լ����Ӧһ��ȡ������Ӧ����Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnUnSubOrderBook(XTPST *ticker, XTPRI *error_info, bool is_last) {};

			///���鶩����֪ͨ���˺����ӿ�Ϊ�����ӿڣ������ݲ�֧�֣�
			///@param order_book ���鶩�������ݣ���Ҫ���ٷ��أ���������������Ϣ������������ʱ���ᴥ������
			virtual void OnOrderBook(XTPOB *order_book) {};


			///��ѯ�ɽ��׺�Լ��Ӧ��
			///@param ticker_info �ɽ��׺�Լ��Ϣ
			///@param error_info ��ѯ�ɽ��׺�Լʱ��������ʱ���صĴ�����Ϣ����error_infoΪ�գ�����error_info.error_idΪ0ʱ������û�д���
			///@param is_last �Ƿ�˴β�ѯ�ɽ��׺�Լ�����һ��Ӧ�𣬵�Ϊ���һ����ʱ��Ϊtrue�����Ϊfalse����ʾ��������������Ϣ��Ӧ
			virtual void OnQueryAllTickers(XTPQSI* ticker_info, XTPRI *error_info, bool is_last) {};
		};
	}
}

#ifndef WINDOWS
#if __GNUC__ >= 4
#pragma GCC visibility push(default)
#endif
#endif

/*!
* \class XTP::API::QuoteApi
*
* \brief ���鶩�Ľӿ���
*
* \author ��̩֤ȯ�ɷ����޹�˾
* \date ʮ�� 2015
*/
namespace XTP {
	namespace API {
		class MD_API_EXPORT QuoteApi
		{
		public:
			///����QuoteApi
			///@param client_id ���������룩��������ͬһ�û��Ĳ�ͬ�ͻ��ˣ����û��Զ���
			///@param save_file_path ���������룩����������Ϣ�ļ���Ŀ¼�����趨һ���п�дȨ�޵���ʵ���ڵ�·��
			///@param log_level ��־�������
			///@return ��������UserApi
			///@remark ���һ���˻���Ҫ�ڶ���ͻ��˵�¼����ʹ�ò�ͬ��client_id��ϵͳ����һ���˻�ͬʱ��¼����ͻ��ˣ����Ƕ���ͬһ�˻�����ͬ��client_idֻ�ܱ���һ��session���ӣ�����ĵ�¼��ǰһ��session�����ڼ䣬�޷�����
			static QuoteApi *CreateQuoteApi(uint8_t client_id, const char *save_file_path, XTP_LOG_LEVEL log_level=XTP_LOG_LEVEL_DEBUG);

			///ɾ���ӿڶ�����
			///@remark ����ʹ�ñ��ӿڶ���ʱ,���øú���ɾ���ӿڶ���
			virtual void Release() = 0;


			///��ȡ��ǰ������
			///@return ��ȡ���Ľ�����
			///@remark ֻ�е�¼�ɹ���,���ܵõ���ȷ�Ľ�����
			virtual const char *GetTradingDay() = 0;

			///��ȡAPI�ķ��а汾��
			///@return ����api���а汾��
			virtual const char* GetApiVersion() = 0;

			///��ȡAPI��ϵͳ����
			///@return ���صĴ�����Ϣ��������Login��Logout�����ġ�ȡ������ʧ��ʱ���ã���ȡʧ�ܵ�ԭ��
			///@remark �����ڵ���api�ӿ�ʧ��ʱ���ã�����loginʧ��ʱ
			virtual XTPRI *GetApiLastError() = 0;


			///ע��ص��ӿ�
			///@param spi �����Իص��ӿ����ʵ�������ڵ�¼֮ǰ�趨
			virtual void RegisterSpi(QuoteSpi *spi) = 0;

			///�������顣
			///@return ���Ľӿڵ����Ƿ�ɹ�����0����ʾ�ӿڵ��óɹ����ǡ�0����ʾ�ӿڵ��ó���
			///@param ticker ��ԼID���飬ע���Լ���������'\0'��β���������ո� 
			///@param count Ҫ����/�˶�����ĺ�Լ����
			///@param exchage_id ����������
			///@remark ����һ���Զ���ͬһ֤ȯ�������Ķ����Լ�������û���Ϊ����������Ҫ���µ�¼���������������Ҫ���¶�������
			virtual int SubscribeMarketData(char *ticker[], int count, XTP_EXCHANGE_TYPE exchage_id) = 0;

			///�˶����顣
			///@return ȡ�����Ľӿڵ����Ƿ�ɹ�����0����ʾ�ӿڵ��óɹ����ǡ�0����ʾ�ӿڵ��ó���
			///@param ticker ��ԼID���飬ע���Լ���������'\0'��β���������ո�  
			///@param count Ҫ����/�˶�����ĺ�Լ����
			///@param exchage_id ����������
			///@remark ����һ����ȡ������ͬһ֤ȯ�������Ķ����Լ
			virtual int UnSubscribeMarketData(char *ticker[], int count, XTP_EXCHANGE_TYPE exchage_id) = 0;

			///�������鶩������(�˺����ӿ�Ϊ�����ӿڣ������ݲ�֧��)
			///@return �������鶩�����ӿڵ����Ƿ�ɹ�����0����ʾ�ӿڵ��óɹ����ǡ�0����ʾ�ӿڵ��ó���
			///@param ticker ��ԼID���飬ע���Լ���������'\0'��β���������ո� 
			///@param count Ҫ����/�˶����鶩�����ĺ�Լ����
			///@param exchage_id ����������
			///@remark ����һ���Զ���ͬһ֤ȯ�������Ķ����Լ�������û���Ϊ����������Ҫ���µ�¼���������������Ҫ���¶�������(�ݲ�֧��)
			virtual int SubscribeOrderBook(char *ticker[], int count, XTP_EXCHANGE_TYPE exchage_id) = 0;

			///�˶����鶩������(�˺����ӿ�Ϊ�����ӿڣ������ݲ�֧��)
			///@return ȡ���������鶩�����ӿڵ����Ƿ�ɹ�����0����ʾ�ӿڵ��óɹ����ǡ�0����ʾ�ӿڵ��ó���
			///@param ticker ��ԼID���飬ע���Լ���������'\0'��β���������ո�  
			///@param count Ҫ����/�˶����鶩�����ĺ�Լ����
			///@param exchage_id ����������
			///@remark ����һ����ȡ������ͬһ֤ȯ�������Ķ����Լ(�ݲ�֧��)
			virtual int UnSubscribeOrderBook(char *ticker[], int count, XTP_EXCHANGE_TYPE exchage_id) = 0;

			///�û���¼����
			///@return ��¼�Ƿ�ɹ�����0����ʾ��¼�ɹ�����-1����ʾ���ӷ�����������ʱ�û����Ե���GetApiLastError()����ȡ������룬��-2����ʾ�Ѵ������ӣ��������ظ���¼�������Ҫ����������logout����-3����ʾ�����д���
			///@param ip ������ip��ַ�����ơ�127.0.0.1��
			///@param port �������˿ں�
			///@param user ��½�û���
			///@param password ��½����
			///@param sock_type ��1������TCP����2������UDP��Ŀǰ��ʱֻ֧��TCP
			///@remark �˺���Ϊͬ������ʽ������Ҫ�첽�ȴ���¼�ɹ������������ؼ��ɽ��к�����������apiֻ����һ������
			virtual int Login(const char* ip, int port, const char* user, const char* password, XTP_PROTOCOL_TYPE sock_type) = 0;


			///�ǳ�����
			///@return �ǳ��Ƿ�ɹ�����0����ʾ�ǳ��ɹ����ǡ�0����ʾ�ǳ�������ʱ�û����Ե���GetApiLastError()����ȡ�������
			///@remark �˺���Ϊͬ������ʽ������Ҫ�첽�ȴ��ǳ������������ؼ��ɽ��к�������
			virtual int Logout() = 0;

			///��ȡ��ǰ�����տɽ��׺�Լ
			///@return ��ѯ�Ƿ�ɹ�����0����ʾ��ѯ�ɹ����ǡ�0����ʾ��ѯ���ɹ�
			///@param exchage_id ����������
			virtual int QueryAllTickers(XTP_EXCHANGE_TYPE exchage_id) = 0;


		protected:
			~QuoteApi() {};
		};
	}
}

#ifndef WINDOWS
#if __GNUC__ >= 4
#pragma GCC visibility pop
#endif
#endif


#endif
