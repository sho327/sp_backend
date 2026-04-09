from django.core.mail.backends import console
from email.header import decode_header, make_header

class ReadableSubjectEmailBackend(console.EmailBackend):
    def write_message(self, message):
        # メッセージオブジェクトを一度だけ取得
        msg_obj = message.message()
        
        # 1. Subjectのデコードと表示
        subject_raw = msg_obj.get('Subject')
        if subject_raw:
            # make_headerを使うと、エンコードされたヘッダーを安全にデコードして文字列化できる
            readable_subject = str(make_header(decode_header(subject_raw)))
            self.stream.write(f'\nSubject (日本語表示): {readable_subject}\n')

        # 2. Bodyのデコードと表示
        try:
            if msg_obj.is_multipart():
                for part in msg_obj.walk():
                    if part.get_content_type() == 'text/plain':
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset)
                        self.stream.write(f'Body (日本語表示):\n{body}\n')
            else:
                charset = msg_obj.get_content_charset() or 'utf-8'
                body = msg_obj.get_payload(decode=True).decode(charset)
                self.stream.write(f'Body (日本語表示):\n{body}\n')
        except Exception as e:
            self.stream.write(f'-- Body decode error: {e} --\n')

        # 3. 最後に親クラスの標準出力（Base64等）を表示
        super().write_message(message)